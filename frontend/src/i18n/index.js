import { createI18n } from 'vue-i18n'
import languages from '../../../locales/languages.json'

const localeFiles = import.meta.glob('../../../locales/!(languages).json', { eager: true })

const messages = {}
const availableLocales = []

for (const path in localeFiles) {
  const key = path.match(/\/([^/]+)\.json$/)[1]
  if (languages[key]) {
    messages[key] = localeFiles[path].default
    availableLocales.push({ key, label: languages[key].label })
  }
}

// Migration note: 'zh' was retired (zh.json removed). If a user still has
// localStorage.locale === 'zh', map them to 'es' so the UI doesn't fall
// back to keys.
const storedLocale = localStorage.getItem('locale')
const savedLocale = storedLocale && storedLocale !== 'zh' ? storedLocale : 'es'

const i18n = createI18n({
  legacy: false,
  locale: savedLocale,
  fallbackLocale: 'en',
  messages
})

export { availableLocales }
export default i18n
