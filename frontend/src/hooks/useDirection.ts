import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { isRTL } from "../i18n";

export function useDirection() {
  const { i18n } = useTranslation();
  useEffect(() => {
    const dir = isRTL(i18n.language) ? "rtl" : "ltr";
    document.documentElement.setAttribute("dir", dir);
    document.documentElement.setAttribute("lang", i18n.language);
  }, [i18n.language]);
}
