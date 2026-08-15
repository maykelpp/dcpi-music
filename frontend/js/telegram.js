// Integración con Telegram Web Apps — https://core.telegram.org/bots/webapps
const TG = window.Telegram?.WebApp;

const DcpiTelegram = (() => {
  if (TG) {
    TG.ready();
    TG.expand();
    TG.setHeaderColor?.('#0B0B10');
    TG.setBackgroundColor?.('#0B0B10');
    TG.enableClosingConfirmation?.();
  }

  function getInitData() {
    // initData crudo — el backend lo valida con HMAC. Nunca se confía en
    // el user object del cliente para nada sensible.
    return TG?.initData || '';
  }

  function getUser() {
    return TG?.initDataUnsafe?.user || null;
  }

  function hapticImpact(style = 'light') {
    TG?.HapticFeedback?.impactOccurred(style);
  }

  function onBackButton(cb) {
    if (!TG) return;
    TG.BackButton.onClick(cb);
  }

  function showBackButton(show) {
    if (!TG) return;
    show ? TG.BackButton.show() : TG.BackButton.hide();
  }

  return { getInitData, getUser, hapticImpact, onBackButton, showBackButton, isTelegram: !!TG };
})();
