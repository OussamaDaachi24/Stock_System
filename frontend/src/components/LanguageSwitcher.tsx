import { useTranslation } from "react-i18next";

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const current = i18n.language.startsWith("ar") ? "ar" : "en";

  function onChange(e: React.ChangeEvent<HTMLSelectElement>) {
    void i18n.changeLanguage(e.target.value);
  }

  return (
    <select
      className="input lang-switcher"
      value={current}
      onChange={onChange}
      aria-label="Language"
    >
      <option value="en">EN</option>
      <option value="ar">العربية</option>
    </select>
  );
}
