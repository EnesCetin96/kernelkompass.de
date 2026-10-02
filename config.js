// KernelKompass — Ortak yapılandırma dosyası
// Bu dosya webapp/index.html, webapp/verify-email.html,
// webapp/reset-password.html ve website/index.html tarafından
// ORTAK olarak kullanılır. Backend adresi değişirse SADECE burası
// güncellenir, dört dosyayı tek tek düzenlemeye gerek kalmaz.
//
// null = backend yok (statik barındırma, örn. GitHub Pages) -> DEMO MODU:
// uygulama giriş istemeden açılır, notlar/ilerleme sadece tarayıcıda
// (localStorage) saklanır; hesap, senkron ve yorumlar kapalıdır.
// Backend'i tekrar yayına alınca adresini yaz, örn. 'https://kernelkompass.de'.
window.KK_API_BASE = null;
