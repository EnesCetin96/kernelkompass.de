/**
 * KernelKompass — Uçtan Uca Smoke Test (Playwright)
 * =================================================
 * Kayıt/giriş, tüm bölüm navigasyonu (404/JS hatası taraması dahil —
 * 3 Ağustos'taki "sections/ 700 izin" hatasının bir benzeri tekrar
 * olursa burada yakalanır), dosya yöneticisi, mini terminal, sınav
 * (MC kısmı tam otomatik), PWA manifest/service-worker sağlık kontrolü.
 *
 * KURULUM (bir kere):
 *   npm install -D playwright
 *   npx playwright install chromium
 *
 * ÇALIŞTIRMA — İKİ MOD:
 *
 *  1) Var olan (e-postası zaten doğrulanmış) bir test hesabıyla:
 *     node kk-e2e-test.js login <kullaniciadi_veya_email> <sifre>
 *
 *  2) Yeni kayıt (script kayıt olur, doğrulama e-postasını bekler,
 *     sen linke tıklayıp doğruladıktan sonra terminalde Enter'a
 *     basarsın, script login ile devam eder):
 *     node kk-e2e-test.js register <kullaniciadi> <email> <sifre> [tr|de]
 *
 * Örnek:
 *   node kk-e2e-test.js login testuser Sifre123
 *   node kk-e2e-test.js register kktest01 kktest01@example.com Sifre123 tr
 *
 * Çıktı: konsola adım adım OK/HATA, hata varsa /tmp benzeri bir klasöre
 * (BASE_DIR/screenshots) ekran görüntüsü kaydeder.
 */

const { chromium } = require('playwright');
const readline = require('readline');
const fs = require('fs');
const path = require('path');

const BASE_URL = 'https://kernelkompass.de/webapp/';
const SCREENSHOT_DIR = path.join(__dirname, 'kk-test-screenshots');
if (!fs.existsSync(SCREENSHOT_DIR)) fs.mkdirSync(SCREENSHOT_DIR);

let failures = 0;
let warnings = 0;

function ok(msg) { console.log('  \x1b[32m✓\x1b[0m ' + msg); }
function bad(msg) { console.log('  \x1b[31m✗\x1b[0m ' + msg); failures++; }
function warn(msg) { console.log('  \x1b[33m!\x1b[0m ' + msg); warnings++; }
function section(title) { console.log('\n\x1b[1m== ' + title + ' ==\x1b[0m'); }

async function shot(page, name) {
  try {
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, name + '.png') });
  } catch (e) { /* ignore */ }
}

function waitForEnter(promptText) {
  return new Promise((resolve) => {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    rl.question(promptText, () => { rl.close(); resolve(); });
  });
}

async function main() {
  const mode = process.argv[2];
  if (mode !== 'login' && mode !== 'register') {
    console.log('Kullanım:');
    console.log('  node kk-e2e-test.js login <kullaniciadi_veya_email> <sifre>');
    console.log('  node kk-e2e-test.js register <kullaniciadi> <email> <sifre> [tr|de]');
    process.exit(1);
  }

  const browser = await chromium.launch({ headless: false, slowMo: 50 });
  const context = await browser.newContext();
  const page = await context.newPage();

  const consoleErrors = [];
  const failedRequests = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('requestfailed', (req) => {
    failedRequests.push(req.url() + ' — ' + (req.failure()?.errorText || '?'));
  });
  page.on('response', (res) => {
    if (res.status() >= 400) {
      failedRequests.push(res.url() + ' — HTTP ' + res.status());
    }
  });

  section('Sayfa yükleme');
  await page.goto(BASE_URL, { waitUntil: 'networkidle' });
  ok('index.html yüklendi: ' + BASE_URL);

  // ---- PWA sağlık kontrolü (manifest + service worker) ----
  section('PWA altyapı kontrolü (manifest.json + sw.js)');
  const manifestHref = await page.getAttribute('link[rel="manifest"]', 'href').catch(() => null);
  if (manifestHref) {
    const manifestUrl = new URL(manifestHref, BASE_URL).href;
    const res = await page.request.get(manifestUrl);
    if (res.ok()) {
      const json = await res.json().catch(() => null);
      if (json && json.icons && json.icons.length > 0) {
        ok('manifest.json 200 döndü, ' + json.icons.length + ' ikon tanımlı');
      } else {
        warn('manifest.json 200 ama icons alanı boş/eksik görünüyor');
      }
    } else {
      bad('manifest.json HTTP ' + res.status());
    }
  } else {
    bad('<link rel="manifest"> bulunamadı');
  }
  const swState = await page.evaluate(async () => {
    if (!('serviceWorker' in navigator)) return 'unsupported';
    try {
      const reg = await navigator.serviceWorker.getRegistration();
      if (reg) return 'registered:' + (reg.active ? reg.active.state : 'no-active');
      // henüz register olmadıysa birkaç saniye bekleyip tekrar dene
      await new Promise(r => setTimeout(r, 2000));
      const reg2 = await navigator.serviceWorker.getRegistration();
      return reg2 ? 'registered-after-wait:' + (reg2.active ? reg2.active.state : 'no-active') : 'not-registered';
    } catch (e) { return 'error:' + e.message; }
  });
  if (swState.startsWith('registered')) ok('Service worker kayıtlı (' + swState + ')');
  else bad('Service worker kayıtlı DEĞİL (' + swState + ') — sw.js yüklenmemiş/hatalı olabilir');
  warn('Native "Ana ekrana ekle" istemi Playwright ile tetiklenemez — bunu elle test et (Chrome adres çubuğunda kurulum ikonu görünmeli).');

  // ---- Auth ----
  if (mode === 'register') {
    const [, , , username, email, password, lang] = process.argv;
    if (!username || !email || !password) {
      console.log('register modu için: node kk-e2e-test.js register <kullaniciadi> <email> <sifre> [tr|de]');
      process.exit(1);
    }
    section('Kayıt (' + username + ' / ' + email + ')');
    await page.click('[data-authtab="register"]');
    await page.fill('#kkRegUsername', username);
    await page.fill('#kkRegEmail', email);
    await page.fill('#kkRegPassword', password);
    if (lang === 'de') await page.selectOption('#kkRegLang', 'de');
    await page.click('#kkRegisterForm button[type="submit"]');
    await page.waitForTimeout(1500);
    const regMsg = await page.textContent('#kkRegMsg').catch(() => '');
    console.log('  Sunucu mesajı: ' + (regMsg || '(boş)'));
    await shot(page, '01-register-result');
    await waitForEnter('\n>>> E-postana gelen doğrulama linkine tıkla, doğruladıktan sonra buraya dönüp ENTER\'a bas...\n');
    await page.reload({ waitUntil: 'networkidle' });
  }

  const loginUser = mode === 'login' ? process.argv[3] : process.argv[4];
  const loginPass = mode === 'login' ? process.argv[4] : process.argv[5];
  if (!loginUser || !loginPass) {
    console.log('Giriş bilgisi eksik.');
    process.exit(1);
  }

  section('Giriş yapılıyor (' + loginUser + ')');
  await page.click('[data-authtab="login"]').catch(() => {});
  await page.fill('#kkLoginIdentifier', loginUser);
  await page.fill('#kkLoginPassword', loginPass);
  await page.click('#kkLoginForm button[type="submit"]');
  await page.waitForTimeout(2000);
  const stillLocked = await page.evaluate(() => document.body.classList.contains('kk-locked'));
  if (stillLocked) {
    const loginMsg = await page.textContent('#kkLoginMsg').catch(() => '');
    bad('Giriş başarısız görünüyor. Sunucu mesajı: ' + loginMsg);
    await shot(page, '02-login-failed');
    console.log('\nGirişsiz devam edilemez, çıkılıyor.');
    await browser.close();
    process.exit(1);
  }
  ok('Giriş başarılı, kk-locked kaldırıldı');
  await shot(page, '02-login-ok');

  // ---- Tüm bölümleri sırayla gez (404 / JS hata taraması) ----
  section('Tüm bölümler geziliyor (fetch 404 + console hata taraması)');
  const targets = await page.$$eval('.navitem[data-target]', els => els.map(e => e.getAttribute('data-target')));
  ok(targets.length + ' navitem bulundu: ' + targets.join(', '));
  for (const target of targets) {
    consoleErrors.length = 0;
    failedRequests.length = 0;
    await page.click('.navitem[data-target="' + target + '"]').catch(async (e) => {
      bad(target + ': tıklanamadı — ' + e.message);
    });
    await page.waitForTimeout(600);
    const panelText = await page.evaluate((id) => {
      const el = document.getElementById(id);
      return el ? el.innerText.trim().length : -1;
    }, target).catch(() => -1);
    if (panelText <= 0) {
      bad(target + ': panel boş görünüyor (içerik uzunluğu ' + panelText + ')');
      await shot(page, 'section-' + target + '-empty');
    } else if (failedRequests.length > 0) {
      bad(target + ': ağ hatası — ' + failedRequests.join('; '));
    } else if (consoleErrors.length > 0) {
      warn(target + ': console hatası — ' + consoleErrors.join('; '));
    } else {
      ok(target + ': OK (' + panelText + ' karakter)');
    }
  }

  // ---- Dosya yöneticisi ----
  section('Dosya Yöneticisi (My Files)');
  consoleErrors.length = 0; failedRequests.length = 0;
  await page.click('#abFiles');
  await page.waitForTimeout(500);
  const fmVisible = await page.isVisible('#sec-files').catch(() => false);
  if (fmVisible) ok('Dosya yöneticisi paneli açıldı');
  else bad('Dosya yöneticisi paneli açılamadı');
  await shot(page, '03-file-manager');

  // ---- Mini terminal ----
  section('Terminal (temel komutlar)');
  await page.click('.navitem[data-target="sec-term"]').catch(() => {});
  await page.waitForTimeout(400);
  const termInput = await page.$('#termInput');
  if (termInput) {
    await termInput.fill('pwd');
    await termInput.press('Enter');
    await page.waitForTimeout(300);
    await termInput.fill('ls');
    await termInput.press('Enter');
    await page.waitForTimeout(300);
    ok('pwd/ls komutları gönderildi (çıktıyı ekran görüntüsünden gözle kontrol et)');
    await shot(page, '04-terminal');
  } else {
    bad('#termInput bulunamadı — terminal engine yüklenmemiş olabilir');
  }

  // ---- Sınav (MC kısmı otomatik, senaryo kısmı elle) ----
  section('Sınav (Level Completion Exam) — MC kısmı');
  await page.click('.navitem[data-target="sec-exam"]').catch(() => {});
  await page.waitForTimeout(500);
  const startBtn = await page.$('#examIntro button');
  if (startBtn) {
    await startBtn.click();
    await page.waitForTimeout(500);
    const mcVisible = await page.isVisible('#examMC');
    if (mcVisible) {
      const radios = await page.$$('#examMC .mcq-options input[type="radio"]');
      ok(radios.length + ' cevap seçeneği (radio) bulundu, her sorunun ilk seçeneği işaretleniyor');
      const seen = new Set();
      for (const r of radios) {
        const name = await r.getAttribute('name');
        if (seen.has(name)) continue;
        seen.add(name);
        await r.check().catch(() => {});
      }
      await shot(page, '05-exam-mc-answered');
      const gotoBtn = await page.$('#examMC button');
      if (gotoBtn) {
        await gotoBtn.click();
        await page.waitForTimeout(500);
        const scenarioVisible = await page.isVisible('#examScenario');
        if (scenarioVisible) {
          ok('Senaryo kısmına geçildi.');
          await shot(page, '06-exam-scenario-start');
          warn('Senaryo kısmı (5 uygulamalı görev, gerçek terminalde) her soruya özgü çözüm gerektirir — otomatik çözülemedi. Tarayıcı açık kaldı, buradan elle devam edebilirsin.');
        } else {
          bad('Senaryo paneline geçilemedi');
        }
      } else {
        bad('"Senaryolara geç" butonu bulunamadı');
      }
    } else {
      bad('Sınav başlatıldı ama #examMC görünmüyor');
    }
  } else {
    bad('Sınav başlat butonu (#examIntro button) bulunamadı');
  }

  section('ÖZET');
  console.log('  Hata (✗): ' + failures);
  console.log('  Uyarı (!): ' + warnings);
  console.log('  Ekran görüntüleri: ' + SCREENSHOT_DIR);
  console.log('\nTarayıcı açık bırakıldı — senaryo kısmını elle bitirmek, PWA kurulumunu\ndenemek veya başka bir şeye bakmak istersen kullanabilirsin. Bitirince\nterminalde Ctrl+C ile script\'i kapatabilirsin.');
}

main().catch((e) => {
  console.error('BEKLENMEYEN HATA:', e);
  process.exit(1);
});
