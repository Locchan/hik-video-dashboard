(function (global) {
  var DEFAULT_LANG = "en";
  var SUPPORTED = { en: true, ru: true };
  var STORAGE_KEY = "hvd_lang";

  var DICT = {
    en: {
      "login.title": "Login — HIK Video Dashboard",
      "login.heading": "Login",
      "login.username": "Username",
      "login.password": "Password",
      "login.submit": "Sign in",
      "login.required": "Username and password are required.",
      "login.failed": "Login failed.",
      "login.network": "Network error.",
      "login.pwd_changed": "Password updated. Sign in with your new password.",

      "header.brand": "HIK Video Dashboard",
      "header.nav.configuration": "Configuration",
      "header.nav.alerts": "Alerts",
      "header.logout": "Log out",
      "footer.backend": "backend",
      "footer.frontend": "frontend",
      "footer.purest": "purest",

      "alerts.title": "Alerts — HIK Video Dashboard",
      "alerts.heading": "Alerts",
      "alerts.empty": "No alerts found.",
      "alerts.load_failed": "Failed to load alerts.",
      "alerts.thumb_error": "Could not get thumbnail",
      "alerts.play": "Play",
      "alerts.video_failed": "Could not load video.",
      "alerts.video_close": "Close",
      "alerts.day.today": "Today",
      "alerts.day.yesterday": "Yesterday",
      "alerts.month.1": "January",
      "alerts.month.2": "February",
      "alerts.month.3": "March",
      "alerts.month.4": "April",
      "alerts.month.5": "May",
      "alerts.month.6": "June",
      "alerts.month.7": "July",
      "alerts.month.8": "August",
      "alerts.month.9": "September",
      "alerts.month.10": "October",
      "alerts.month.11": "November",
      "alerts.month.12": "December",
      "alerts.date.en": "{month} {day} {year}",
      "alerts.date.ru": "{day} {month} {year}",

      "app.title": "HIK Video Dashboard",
      "app.heading": "Home",
      "app.empty": "No feature panels are available yet. Use Configuration to manage the system.",
      "app.section.alerts.desc": "Browse camera alert clips and play recordings.",
      "app.section.configuration.desc": "Manage config entries, account, users, and feature flags.",

      "config.title": "Configuration — HIK Video Dashboard",
      "config.heading": "Configuration",
      "config.new": "New entry",
      "config.logout": "Log out",
      "config.disabled": "The configuration feature is disabled.",
      "config.entries.heading": "Config entries",
      "config.col.key": "Key",
      "config.col.value": "Value",
      "config.col.actions": "Actions",
      "config.placeholder.key": "key",
      "config.placeholder.value": "value",
      "config.submit": "submit",
      "config.edit": "edit",
      "config.delete": "delete",
      "config.confirm": "confirm",
      "config.load_failed": "Failed to load config.",
      "config.create_failed": "Create failed.",
      "config.update_failed": "Update failed.",
      "config.delete_failed": "Delete failed.",
      "config.key_empty": "Key must not be empty.",
      "config.value_empty": "Value must not be empty.",
      "config.key_exists": "Key already exists for your group.",

      "account.heading": "Account",
      "account.language": "Language",
      "account.lang.en": "English",
      "account.lang.ru": "Russian",
      "account.new_password": "New password",
      "account.confirm_password": "Confirm password",
      "account.change_password": "Change my password",
      "account.pwd_min": "Password must be at least 8 characters.",
      "account.pwd_mismatch": "Passwords do not match.",
      "account.pwd_failed": "Password change failed.",

      "users.heading": "Users",
      "users.create": "Create user",
      "users.username": "Username",
      "users.password": "Password",
      "users.create_btn": "Create",
      "users.col.username": "Username",
      "users.col.group": "Group",
      "users.col.loginable": "Loginable",
      "users.col.set_password": "Set password",
      "users.yes": "yes",
      "users.no": "no",
      "users.pwd_placeholder": "new password",
      "users.pwd_set": "set",
      "users.load_failed": "Failed to load users.",
      "users.create_failed": "Create user failed.",
      "users.username_min": "Username must be at least 4 characters.",
      "users.pwd_updated": "Password updated for {user} (sessions expired).",

      "features.heading": "Features",
      "features.load_failed": "Failed to load features.",
      "features.update_failed": "Failed to update feature.",
      "features.enabled": "Enabled",
      "features.col.name": "Name",
      "features.col.description": "Description",
      "features.col.enabled": "Enabled",
      "feature.CONFIG.title": "Configuration",
      "feature.CONFIG.desc": "Group configuration key/value store and editor.",
      "feature.ALERT_VIEW.title": "Alerts",
      "feature.ALERT_VIEW.desc": "Browse camera alert clips with nearest-snap thumbnails.",
    },
    ru: {
      "login.title": "Вход — HIK Video Dashboard",
      "login.heading": "Вход",
      "login.username": "Имя пользователя",
      "login.password": "Пароль",
      "login.submit": "Войти",
      "login.required": "Нужны имя пользователя и пароль.",
      "login.failed": "Не удалось войти.",
      "login.network": "Ошибка сети.",
      "login.pwd_changed": "Пароль обновлён. Войдите с новым паролем.",

      "header.brand": "HIK Video Dashboard",
      "header.nav.configuration": "Настройки",
      "header.nav.alerts": "Тревоги",
      "header.logout": "Выйти",
      "footer.backend": "backend",
      "footer.frontend": "frontend",
      "footer.purest": "purest",

      "alerts.title": "Тревоги — HIK Video Dashboard",
      "alerts.heading": "Тревоги",
      "alerts.empty": "Тревог не найдено.",
      "alerts.load_failed": "Не удалось загрузить тревоги.",
      "alerts.thumb_error": "Не удалось получить миниатюру",
      "alerts.play": "Играть",
      "alerts.video_failed": "Не удалось загрузить видео.",
      "alerts.video_close": "Закрыть",
      "alerts.day.today": "Сегодня",
      "alerts.day.yesterday": "Вчера",
      "alerts.month.1": "Января",
      "alerts.month.2": "Февраля",
      "alerts.month.3": "Марта",
      "alerts.month.4": "Апреля",
      "alerts.month.5": "Мая",
      "alerts.month.6": "Июня",
      "alerts.month.7": "Июля",
      "alerts.month.8": "Августа",
      "alerts.month.9": "Сентября",
      "alerts.month.10": "Октября",
      "alerts.month.11": "Ноября",
      "alerts.month.12": "Декабря",
      "alerts.date.en": "{month} {day} {year}",
      "alerts.date.ru": "{day} {month} {year}",

      "app.title": "HIK Video Dashboard",
      "app.heading": "Главная",
      "app.empty": "Панели функций пока недоступны. Управляйте системой через Настройки.",
      "app.section.alerts.desc": "Просмотр тревог с камер и воспроизведение записей.",
      "app.section.configuration.desc": "Записи конфигурации, аккаунт, пользователи и флаги функций.",

      "config.title": "Настройки — HIK Video Dashboard",
      "config.heading": "Настройки",
      "config.new": "Создать",
      "config.logout": "Выйти",
      "config.disabled": "Функция настроек отключена.",
      "config.entries.heading": "Записи конфигурации",
      "config.col.key": "Ключ",
      "config.col.value": "Значение",
      "config.col.actions": "Действия",
      "config.placeholder.key": "ключ",
      "config.placeholder.value": "значение",
      "config.submit": "сохранить",
      "config.edit": "изменить",
      "config.delete": "удалить",
      "config.confirm": "подтвердить",
      "config.load_failed": "Не удалось загрузить настройки.",
      "config.create_failed": "Не удалось создать.",
      "config.update_failed": "Не удалось обновить.",
      "config.delete_failed": "Не удалось удалить.",
      "config.key_empty": "Ключ не должен быть пустым.",
      "config.value_empty": "Значение не должно быть пустым.",
      "config.key_exists": "Такой ключ уже есть в вашей группе.",

      "account.heading": "Аккаунт",
      "account.language": "Язык",
      "account.lang.en": "Английский",
      "account.lang.ru": "Русский",
      "account.new_password": "Новый пароль",
      "account.confirm_password": "Подтвердите пароль",
      "account.change_password": "Сменить пароль",
      "account.pwd_min": "Пароль должен быть не короче 8 символов.",
      "account.pwd_mismatch": "Пароли не совпадают.",
      "account.pwd_failed": "Не удалось сменить пароль.",

      "users.heading": "Пользователи",
      "users.create": "Создать пользователя",
      "users.username": "Имя пользователя",
      "users.password": "Пароль",
      "users.create_btn": "Создать",
      "users.col.username": "Имя",
      "users.col.group": "Группа",
      "users.col.loginable": "Вход",
      "users.col.set_password": "Сменить пароль",
      "users.yes": "да",
      "users.no": "нет",
      "users.pwd_placeholder": "новый пароль",
      "users.pwd_set": "задать",
      "users.load_failed": "Не удалось загрузить пользователей.",
      "users.create_failed": "Не удалось создать пользователя.",
      "users.username_min": "Имя должно быть не короче 4 символов.",
      "users.pwd_updated": "Пароль обновлён для {user} (сессии сброшены).",

      "features.heading": "Функции",
      "features.load_failed": "Не удалось загрузить функции.",
      "features.update_failed": "Не удалось обновить функцию.",
      "features.enabled": "Включено",
      "features.col.name": "Имя",
      "features.col.description": "Описание",
      "features.col.enabled": "Вкл.",
      "feature.CONFIG.title": "Настройки",
      "feature.CONFIG.desc": "Хранилище и редактор ключей конфигурации группы.",
      "feature.ALERT_VIEW.title": "Тревоги",
      "feature.ALERT_VIEW.desc": "Просмотр клипов тревог с ближайшими снимками.",
    },
  };

  var current = DEFAULT_LANG;

  function normalize(value) {
    if (value == null) return DEFAULT_LANG;
    var raw = String(value).trim().toLowerCase();
    if (!raw) return DEFAULT_LANG;
    if (raw === "en" || raw === "eng" || raw === "english" || raw.indexOf("en-") === 0 || raw.indexOf("en_") === 0) {
      return "en";
    }
    if (raw === "ru" || raw === "rus" || raw === "russian" || raw.indexOf("ru-") === 0 || raw.indexOf("ru_") === 0) {
      return "ru";
    }
    return DEFAULT_LANG;
  }

  function systemLanguage() {
    var nav =
      (navigator.languages && navigator.languages[0]) ||
      navigator.language ||
      navigator.userLanguage ||
      DEFAULT_LANG;
    return normalize(nav);
  }

  function t(key, vars) {
    var table = DICT[current] || DICT[DEFAULT_LANG];
    var text = table[key];
    if (text == null) {
      text = (DICT[DEFAULT_LANG] && DICT[DEFAULT_LANG][key]) || key;
    }
    if (vars) {
      Object.keys(vars).forEach(function (k) {
        text = text.replace(new RegExp("\\{" + k + "\\}", "g"), String(vars[k]));
      });
    }
    return text;
  }

  function apply(root) {
    root = root || document;
    var nodes = root.querySelectorAll("[data-i18n]");
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      var key = el.getAttribute("data-i18n");
      if (!key) continue;
      var attr = el.getAttribute("data-i18n-attr");
      var value = t(key);
      if (attr) {
        el.setAttribute(attr, value);
      } else if (el.tagName === "TITLE") {
        el.textContent = value;
      } else if (el.tagName === "BUTTON") {
        el.textContent = value;
      } else if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") {
        el.placeholder = value;
      } else {
        el.textContent = value;
      }
    }
    document.documentElement.lang = current;
  }

  function setLanguage(lang) {
    current = normalize(lang);
    try {
      localStorage.setItem(STORAGE_KEY, current);
    } catch (e) {
      /* ignore */
    }
    apply(document);
    return current;
  }

  function getLanguage() {
    return current;
  }

  function initFromSystem() {
    var stored = null;
    try {
      stored = localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      stored = null;
    }
    if (stored) return setLanguage(stored);
    return setLanguage(systemLanguage());
  }

  global.HVDi18n = {
    DEFAULT_LANG: DEFAULT_LANG,
    SUPPORTED: SUPPORTED,
    normalize: normalize,
    systemLanguage: systemLanguage,
    t: t,
    apply: apply,
    setLanguage: setLanguage,
    getLanguage: getLanguage,
    initFromSystem: initFromSystem,
  };
})(window);
