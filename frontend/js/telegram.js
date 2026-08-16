// Funciona tanto dentro de Telegram (Web App) como en un navegador normal.
const TG = window.Telegram?.WebApp;

const DcpiTelegram = (() => {
  if (TG && TG.initData) {
    TG.ready();
    TG.expand();
    TG.setHeaderColor?.('#0B0B10');
    TG.setBackgroundColor?.('#0B0B10');
    TG.enableClosingConfirmation?.();
  }

  const isTelegram = !!(TG && TG.initData);

  // Si no estamos dentro de Telegram, generamos/persistimos un ID de
  // invitado en el navegador para que historial/favoritos igual funcionen.
  function getGuestId() {
    let id = localStorage.getItem('dcpi_guest_id');
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem('dcpi_guest_id', id);
    }
    return id;
  }

  function getInitData() {
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

  return { getInitData, getGuestId, getUser, hapticImpact, onBackButton, showBackButton, isTelegram };
})();
