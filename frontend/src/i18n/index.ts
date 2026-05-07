import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

const SUPPORTED_LNGS = ["en", "ar"] as const;
export type SupportedLng = (typeof SUPPORTED_LNGS)[number];

export const STORAGE_KEY = "stock_locale_v1";

const modules = import.meta.glob("./locales/*/*.json", { eager: true }) as Record<
  string,
  { default: Record<string, unknown> }
>;

const resources: Record<string, Record<string, Record<string, unknown>>> = {};
for (const [path, mod] of Object.entries(modules)) {
  const m = path.match(/\/locales\/(.+)\/(.+)\.json$/);
  if (!m) continue;
  const [, lng, ns] = m;
  resources[lng] ??= {};
  resources[lng][ns] = mod.default;
}

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    supportedLngs: SUPPORTED_LNGS as unknown as string[],
    fallbackLng: "en",
    defaultNS: "common",
    ns: Object.keys(resources.en ?? {}),
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator"],
      lookupLocalStorage: STORAGE_KEY,
      caches: ["localStorage"],
    },
    returnNull: false,
  });

export default i18n;

export function changeLanguage(lng: SupportedLng) {
  return i18n.changeLanguage(lng);
}

export function isRTL(lng: string = i18n.language): boolean {
  return lng.startsWith("ar") || lng.startsWith("he") || lng.startsWith("fa");
}
