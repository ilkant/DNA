# Testataan kielivaihtoehtoja

# import gettext
# import locale

# user_locale, _ = locale.getdefaultlocale()
# lang = gettext.translation('messages', localedir='locale', languages=[user_locale])
# lang.install()
# _ = lang.gettext

from babel.dates import format_datetime
from datetime import datetime
import locale

locale.setlocale(locale.LC_TIME, "fi_FI.UTF-8")
print(format_datetime(datetime.now(), locale='fi'))