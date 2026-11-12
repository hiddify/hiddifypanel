# Changelog


## (unreleased)

#### Other

* Fix(auth): keep account passwords as salted scrypt hashes. 
  _Admin and user passwords were stored and compared as typed. Now only a
salted scrypt hash is kept (hiddifypanel.passwords), and every sign-in path
checks the password against it.

- Assigning a password stores its hash; "" still means no password.
- Link + password, alias, basic auth and the current-password check use
  check_password (constant time). A correct check is remembered for a few
  minutes in memory, keyed by the stored hash, for API clients that send
  their password on each request.
- Admins keep a password_strong flag (an alias needs a strong password).
- Migration _v208 widens the column and hashes the passwords kept as typed
  (users' with a lighter scrypt, raised at their next sign-in). One kept as
  typed that comes back later, e.g. from an old backup, is hashed at its
  next sign-in._

* Merge branch 'dev' of github.com:hiddify/hiddifypanel into dev. 
  _# Conflicts:
#	hiddifypanel/admin_v2/src/features/inbox/views/InboxView.vue
#	hiddifypanel/panel/init_db.py
#	hiddifypanel/translations.i18n/en.json_

* Merge pull request #213 from Hiddify-Official/fix/inbox-free-test-card. 
  _feat(inbox): several free test packages with private links_

* Feat(inbox): name each free test package. 
  _A Name field in Add Package and Edit Package (one line, up to 40
characters). The card shows the name instead of "Free Test"; the bot
still calls every package Free test, so the admin's own names stay in
the panel._

* Feat(admin_v2): show how each free test package is given on its card. 
  _A chip beside FREE: Manual (amber) or Automatic (green), the colours of
the choice in the package dialog._

* Style(admin_v2): violet icon for private free test packages. 

* Feat(inbox): private links for the packages that are not the default. 
  _Everyone in the bot, and the public link, still get the default package.
Each other package is private: it has its own link (Copy, QR Code,
Telegram on its card) that the admin gives to whom it chooses, and only
that link offers it. The private part of the link is a keyed hash, so the
public link does not lead to the private ones; an unknown one falls back
to the default package. A request waiting keeps the package it asked for._

* Style(admin_v2): gold default package card, coloured live gift icons. 
  _With several packages, the default one's card is a warm gold with a gold
icon that glows; the others keep a coloured icon instead of a grey one.
The icons float softly and the gift rocks now and then (off with reduced
motion)._

* Feat(inbox): several free test packages, the default one offered in the bot. 
  _An admin can keep several free test packages and pick the default one: the
bot and the link offer only the default; the others wait until made the
default. A person still gets one free test in total.

- free_test: the admin's packages are stored as {packages, default} in
  free_package (a single package stored before becomes the only one, and
  the default). A request keeps the id of the package it asked for, and
  approving it later gives that package while it exists.
- Conversation.free_package_id, added by migration _v206.
- Inbox: with one package the page is as before (plus Add Package). With
  several, each package has its own card (Default badge, Make Default,
  Delete) and its conversations in a drawer under it: a live handle that
  opens on a tap or when pulled down, the drawer following the finger._

* Feat(admin_v2): delete the free test package, clearer inbox card. 
  _- Delete Package: turns the admin's own package off and back to the
  defaults, after a confirmation. Shown only for a package of their own.
- The link actions (Copy, QR Code, Telegram) get labels, in their own row.
- Outlines that show on the frosted Caddy and Liquid themes.
- Title case for the inbox's titles and buttons (Edit Package, Copy Link…)._

* Style(admin_v2): give each free test approval mode its own soft colour. 
  _The chosen mode was always a light blue; now "You approve each request"
is a soft amber and "Given automatically" a soft green._

* Style(admin_v2): sit the free test bow on the preview box's corner. 
  _The bow now sits on the top end corner and reaches past the box's edges;
only the ribbon under it stays clipped to the box._

* Style(admin_v2): redraw the free test bow as a satin bow on a diagonal ribbon. 
  _Two loops (up-left, right), two V-cut tails (left, down) and a thick
gathered knot with folds, on a wide ribbon that crosses the box's top end
corner. The tails sway softly and the loops breathe._

* Style(admin_v2): move the free test bow toward the corner, thicken its knot. 

* Style(admin_v2): tie a satin ribbon and bow across the free test preview's corner. 
  _A red satin ribbon now crosses the gift box's top end corner at 45 degrees,
with a two-loop bow on it: the tails sway and the loops breathe softly
(still with reduced motion)._

* Style(admin_v2): hang swaying tails from a tilted bow on the free test preview. 
  _The ribbon band goes; the red bow now sits tilted on the box's top end
corner, and its two tails hang down and sway softly, each at its own pace
(still with reduced motion)._

* Style(admin_v2): tie a red bow on the free test preview. 
  _The gift box preview gets a red ribbon down its end side and a red bow on
its top end corner. "Free test" becomes "Free Test" in the preview and
in the bot's matching titles._

* Style(admin_v2): make the free test preview a gift box. 
  _- Title-case the dialog title and the switch label.
- Give MB and GB their own soft colours in the unit picker.
- Draw the bot preview as a gift box (rose tint, ribbon, bow) with a
  coloured gift icon that shakes now and then (off with reduced motion)._

* Style(admin_v2): give the free test duration and data steppers the same width. 
  _The MB/GB picker sat beside the data stepper and shrank it next to the
duration one. It is now a small iOS-style segmented control in the Data
label row, and the two fields share the row in equal columns._

* Fix(admin_v2): draw the number stepper's border in every theme. 
  _The stepper took its colours from the --p-inputtext-* tokens, which PrimeVue
defines only after an InputText was mounted. On a page without one (the free
test dialog in the inbox) the box and its dividers had no colour and vanished
in light themes. It now uses the global --p-form-field-* tokens._

* Fix(admin_v2): stack the free test duration and data fields on phones. 
  _The two fields stayed side by side on narrow screens, squeezing the data
stepper next to the MB/GB picker. They now share a row only when the
dialog is wide enough, and the unit picker wraps under the stepper on
very small screens._

* Merge pull request #208 from Hiddify-Official/feat/more-languages-v2. 
  _feat(i18n): 22 more panel languages_

* Feat(i18n): translate the admin Telegram message texts in the added languages. 
  _The texts of "message an admin over Telegram" and the "admins" audience of the
broadcast were added to the panel after the new languages were translated.
They are translated in the 22 added languages (the French ones are the
upstream strings)._

* Fix(i18n): keep "Manager" in the menu and use the informal tu in Italian. 
  _- The first menu group is "Manager" (like the HiddifyManager name in the top
  bar), so it is no longer translated in the added languages.
- Italian now uses the informal "tu", as the popular Italian apps and VPN
  clients do, instead of a mix of Lei and impersonal forms._

* Feat(i18n): translate the new Inbox and free-test texts in all added languages. 
  _The Inbox page, the free test package of the Telegram bot and a few proxy
and setting texts were added to the panel after the new languages were
translated. They are now translated in the 22 added languages (150 texts
each). "Hiddify" and technical names stay as they are._

* Feat(i18n): Italian panel language. 
  _Adds Italian (it) for the admin panel and the Lang list:
translations.i18n/it.json, Lang.it, its name and flag in the language
lists. "Hiddify" and technical names stay as they are; placeholders and
HTML are kept._

* Feat(i18n): Dutch panel language. 
  _Adds Dutch (nl) for the admin panel and the Lang list:
translations.i18n/nl.json, Lang.nl, its name and flag in the language
lists. "Hiddify" and technical names stay as they are; placeholders and
HTML are kept._

* Feat(i18n): French panel language. 
  _Adds French (fr) for the admin panel and the Lang list:
translations.i18n/fr.json, Lang.fr, its name and flag in the language
lists. "Hiddify" and technical names stay as they are; placeholders and
HTML are kept._

* Feat(i18n): German panel language. 
  _Adds German (de) for the admin panel and the Lang list:
translations.i18n/de.json, Lang.de, its name and flag in the language
lists. "Hiddify" and technical names stay as they are; placeholders and
HTML are kept._

* Feat(i18n): Hindi panel language. 
  _Adds Hindi (hi, Devanagari) for the admin panel and the Lang list:
translations.i18n/hi.json, Lang.hi, its name and flag in the language
lists. "Hiddify" and technical names stay as they are; placeholders and
HTML are kept._

* Feat(i18n): Ukrainian panel language. 
  _Adds Ukrainian (uk) for the admin panel and the Lang list:
translations.i18n/uk.json, Lang.uk, its name and flag in the language
lists. "Hiddify" and technical names stay as they are; placeholders and
HTML are kept._

* Feat(i18n): Armenian panel language. 
  _Adds Armenian (hy) for the admin panel and the Lang list:
translations.i18n/hy.json, Lang.hy, its name and flag in the language
lists. "Hiddify" and technical names stay as they are; placeholders and
HTML are kept._

* Feat(i18n): Tajik panel language. 
  _Adds Tajik (tg, Cyrillic) for the admin panel and the Lang list:
translations.i18n/tg.json, Lang.tg, its name and flag in the language
lists. "Hiddify" and technical names stay as they are; placeholders and
HTML are kept._

* Feat(i18n): Kyrgyz panel language. 
  _Adds Kyrgyz (ky, Cyrillic) for the admin panel and the Lang list:
translations.i18n/ky.json, Lang.ky, its name and flag in the language
lists. "Hiddify" and technical names stay as they are; placeholders and
HTML are kept._

* Feat(i18n): Kazakh panel language. 
  _Adds Kazakh (kk, Cyrillic) for the admin panel and the Lang list:
translations.i18n/kk.json, Lang.kk, its name and flag in the language
lists. "Hiddify" and technical names stay as they are; placeholders and
HTML are kept._

* Feat(i18n): Azerbaijani panel language. 
  _Adds Azerbaijani (az) for the admin panel and the Lang list:
translations.i18n/az.json, Lang.az, its name and flag in the language
lists. "Hiddify" and technical names stay as they are; placeholders and
HTML are kept._

* Feat(i18n): Uzbek panel language. 
  _Adds Uzbek (uz, Latin script) for the admin panel and the Lang list:
translations.i18n/uz.json, Lang.uz, its name and flag in the language
lists. "Hiddify" and technical names stay as they are; placeholders and
HTML are kept._

* Feat(i18n): Turkish panel language. 
  _Adds Turkish (tr) for the admin panel and the Lang list:
translations.i18n/tr.json, Lang.tr, its name and flag in the language
lists. "Hiddify" and technical names stay as they are; placeholders and
HTML are kept._

* Feat(i18n): Bengali panel language. 
  _Adds Bengali (bn) for the admin panel and the Lang list:
translations.i18n/bn.json, Lang.bn, its name and flag in the language
lists. "Hiddify" and technical names stay as they are; placeholders and
HTML are kept._

* Feat(i18n): Pashto panel language. 
  _Adds Pashto (ps, right to left) for the admin panel and the Lang list:
translations.i18n/ps.json, Lang.ps, its name and flag in the language
lists. "Hiddify" and technical names stay as they are; placeholders and
HTML are kept._

* Feat(i18n): Urdu panel language. 
  _Adds Urdu (ur, right to left) for the admin panel and the Lang list:
translations.i18n/ur.json, Lang.ur, its name and flag in the language
lists. "Hiddify" and technical names stay as they are; placeholders and
HTML are kept._

* Feat(i18n): Arabic panel language. 
  _Adds Arabic (ar, right to left) for the admin panel and the Lang list:
translations.i18n/ar.json, Lang.ar, its name and flag in the language
lists. "Hiddify" and technical names stay as they are; placeholders and
HTML are kept._

* Feat(i18n): Amharic panel language. 
  _Adds Amharic (am, Ge'ez script) for the admin panel and the Lang list:
translations.i18n/am.json, Lang.am, its name and flag in the language
lists. "Hiddify" and technical names stay as they are; placeholders and
HTML are kept._

* Feat(i18n): Spanish panel language. 
  _Adds Spanish (es, neutral Latin American) for the admin panel and the
Lang list: translations.i18n/es.json, Lang.es, its name and flag in the
language lists. "Hiddify" and technical names stay as they are;
placeholders and HTML are kept._

* Feat(i18n): Belarusian panel language. 
  _Adds Belarusian (be, Cyrillic) for the admin panel and the Lang list:
translations.i18n/be.json, Lang.be, its name and flag in the language
lists. "Hiddify" and technical names stay as they are; placeholders and
HTML are kept._

* Feat(i18n): Turkmen panel language. 
  _Adds Turkmen (tk, Latin script) for the admin panel and the Lang list:
translations.i18n/tk.json, Lang.tk, its name and flag in the language
lists. "Hiddify" and technical names stay as they are; placeholders and
HTML are kept._

* Feat(i18n): Korean panel language. 
  _Adds Korean (ko) for the admin panel (admin_v2, settings, the older
server-side messages) and the Lang list. "Hiddify" and technical names
(VLESS, Reality, …) stay as they are; placeholders and HTML are kept.

- translations.i18n/ko.json: the admin UI, settings and server-side
  messages. Texts that are only a code identifier (uri.password) have
  no entry: the panel falls back to English per key.
- Lang.ko, its name and flag in the language lists (admin_v2, settings
  language choices).
- init_db: _v204 expands the accounts' `lang` ENUM columns. Those two
  columns were not in `enum_columns`, so a language added to Lang never
  reached an existing database and saving it as an account's language
  failed ("Data truncated")._

* Refactor(i18n): one list of right-to-left languages. 
  _Right-to-left was decided by `== 'fa'` in several places (the legacy
templates) or by ['fa', 'ar'] (admin_v2), so a new right-to-left
language would have been laid out left to right.

- models.config_enum.RTL_LANGS is the list (fa, ar, ur, ps); the
  templates ask `is_rtl()` instead of comparing with 'fa'.
- admin_v2: isRtlLanguage() in shared/utils/languages.ts, used by the
  document direction, Quick setup and the config tester.

No language is added yet; behaviour is unchanged for the existing ones._

* Merge pull request #210 from Hiddify-Official/fix/pwa-input-zoom. 
  _fix: stop iOS focus zoom in the installed admin and user panels (PWA)_

* Fix(user): stop the iOS focus zoom in the installed user panel (PWA) 

* Fix(admin): stop the iOS focus zoom on every admin page of the installed app. 
  _The served admin_v2 page, the admin login and the legacy Flask-Admin pages
each have their own <head>; add the PWA-only maximum-scale=1 to all of them._

* Fix(admin_v2): stop iOS zooming into focused fields in the installed app (PWA) 

* Feat(auth): sign in to the panel with a passkey. 
  _Admins can sign in with a passkey (fingerprint, face or screen lock) instead
of a password, on every domain of the panel.

- WebAuthn checked in-house with `cryptography` (ES256, EdDSA, RS256; user
  verification required, signature counter checked, one-time challenges).
- One passkey per domain: the sign-in page asks for it by itself when this
  browser has one, and the password form stays as the fallback. An IP gets
  none (browsers only allow passkeys on domain names).
- After a password sign-in, and once on a domain without my passkey, the
  dashboard offers to add one, named after the device.
- My account adds it here, then on the panel's other domains (the sub-link
  domains when there are any) in a frame of each domain's own page, one after
  the other. Each step works with a one-time token kept hashed in Redis, can
  only be framed by the page that asked for it, and signs nobody in.
- Migration _v205 adds the admin_passkey table._

* Feat(inbox): send messages from the inbox. 
  _The Send Message page is merged into Inbox: a Send message button opens the
same composer (everyone, a group or chosen users) in a window. Old /message
links, with their user ids, open the inbox with the window open._

* Merge pull request #209 from Hiddify-Official/fix/qr-plain-size. 
  _fix(admin): plain QR preview no longer fills the page on phones_

* Fix(admin): plain QR preview no longer fills the page on phones. 
  _qrcode sets the canvas's CSS size to its pixel size (preview size x
devicePixelRatio), overriding the 240px preview: 720px tall on a 3x
phone, 480px on a 2x desktop screen. Reset it after drawing._

* Merge pull request #211 from Hiddify-Official/feat/admin-telegram-id. 
  _feat(admins): set an admin's Telegram ID and message admins_

* Feat(admins): message an admin over Telegram from the admins list. 
  _The Telegram chip of an admin now looks like the users page's one and opens
the send-message dialog for that admin. The broadcast API takes
kind=admins: the selected ids are the actor's own sub-admins (or itself)
with a Telegram ID, and the message is sent without a usage report._

* Feat(admins): set an admin's Telegram ID and show it in the admins list. 
  _The admins API now returns and saves telegram_id (validated, one admin per
Telegram account, null clears it). The admin form has the field at the end
of Advanced, like the user form, and admins that have one get a Telegram
chip in the list. The bot already uses it for admin notifications._

* Merge pull request #200 from Hiddify-Official/feat/version-commit. 
  _feat(admin): show the dev version and commit next to DEV_

* Feat(admin): show the dev version and commit next to DEV. 
  _A development panel showed only "DEV" in the top bar, so it was not
clear which code it runs. It now shows "DEV <version> · <short commit>":
the version is the manager's get_commit_version text for that commit
(MM-DDTHH:MM of its commit date in UTC, what the dev update check
compares). Read from hiddifypanel/COMMIT (written by the manager
installer) or, failing that, from the panel's own git checkout. The
label keeps Latin digits in Persian._

* Merge pull request #202 from Hiddify-Official/fix/backup-texts. 
  _fix(admin): title-case the backup page texts_

* Fix(admin): title-case the backup page texts. 

* Merge pull request #203 from Hiddify-Official/feat/admin-permission-colors. 
  _feat(admin): each permission has its own colour in the admin dialog_

* Feat(admin): each permission has its own colour in the admin dialog. 
  _The icon is grey while the permission is off and takes its colour when on;
the summary chips use the same colours._

* Merge pull request #204 from Hiddify-Official/fix/qr-tool-size. 
  _fix(qr-tool): the QR preview never grows past 240px or the screen_

* Fix(qr-tool): the QR preview never grows past 240px or the screen width. 
  _Its size was only in the page's stylesheet: when that file did not load,
the canvas showed at its pixel size (about 630px on a phone), wider than
the screen, and the page clips sideways overflow so it could not be
scrolled or zoomed back. The size is now set on the canvas itself._

* Merge pull request #205 from Hiddify-Official/feat/outbound-option-icons. 
  _feat(admin): coloured vector icons for the default outbound choices_

* Fix(admin): default outbound list shows only the name, "Turned Off" in title case. 
  _The icon already tells the mode, so the small mode label next to each name is gone._

* Feat(admin): coloured vector icons for the default outbound choices. 
  _Each outbound mode has its own SVG icon and colour (Automatic: sparkles,
Direct: arrow, Block: no-entry, WARP: cloud, Socks, Tor, Psiphon, hiddify-core,
Xray) in the admin dialog's and My Account's default outbound picker, in the
list and on the chosen value. A turned-off outbound's icon is grey._

* Merge pull request #206 from Hiddify-Official/fix/config-target-icons. 
  _feat(admin): icons for the additional-config formats_

* Fix(admin): use the official Xray star for the Xray format. 

* Feat(admin): icons for the additional-config formats, labels in title case. 
  _Each format in the additional-configs picker gets a vector mark (the
Hiddify logo, the Xray X, a link, layers for Auto, the Clash cat), in
the list and in the chosen value._

* Merge pull request #207 from Hiddify-Official/feat/free-test-package. 
  _feat(bot): free test package per admin with an inbox_

* Fix(bot): do not show the admin's name to people asking for the free test. 
  _The offer no longer says whose it is, and an admin's answer arrives as "Support".
The name stays in the panel and in the admin's own bot screens._

* Feat(bot): free test package per admin, with an inbox for requests and messages. 
  _Each admin has a link to the Telegram bot (/start free_<code>; the code is a keyed
hash of the admin's uuid, the same after every restart). Whoever opens it sees the
admin's package (for example 7 days, 500 MB, tagged FREE) and asks for it:

- automatic approval gives the account at once, to a Telegram account that never
  had a free test or an account on this panel;
- otherwise the request waits in the admin's inbox until it is approved or declined.

The account is created under that admin, tagged "free" and linked to the chat. A
second free test always needs the admin.

The package is the admin's own when it has the new modify_free_package capability,
else the nearest parent's. Admins get the capability on upgrade; agents use their
parent's package until it is granted.

Everything a non-admin writes to the bot is kept in the new message table and shown
in the new Inbox page of Admin V2, where the admin answers, approves or declines;
the same can be done from Telegram._

* Fix(usage): keep node usage reports in the database and apply each once. 
  _- the node keeps the report in flight in usage_batch_items and resends it
  unchanged until the parent answers; new usage waits in unsynced_usages
- the parent records the last applied report per node in
  applied_usage_batches, in the same transaction as the usage
- replace the per-user committing add_usage_json call with one bulk update
- update the cores and send messages after the commit; failures there are
  logged and do not fail a saved report
- keep the parent's own usage in unsynced_usages when saving fails
- stop renewing the usage lock after 15 minutes
- limit batch_id to 64 characters; migration _v203 creates the tables_

* Fix(usage): apply a node's usage report to the parent only once. 
  _A child node reports its users' traffic to the parent with PUT
/api/v2/parent/usage/. The parent adds the bytes to user.current_usage (the
add_usage_json procedure) and commits, and only then builds and sends its
answer. The report had no identity and the parent never checked for repeats
(request_time was never read).

What went wrong:
- If anything failed after the parent had applied the report (a slow or
  oversized answer, a 5xx, a proxy or CDN cutting the connection, an answer that
  did not parse), the node treated the whole report as failed and kept it in
  unsynced_usages.
- The next report then merged that old usage with the new one and sent it again.
  The parent added it again, and again every minute while syncs kept failing.
  last_users_sync only moves on success, so the parent's answer (every user
  changed since that time) kept growing, which made further failures more likely.
- The HTTP client also resends the same PUT itself: up to 5 times on 502/503/52x,
  up to 3 times on connection errors, and on the next address (direct, relay,
  CDN) when one looks unreachable, each of which can be applied again.

The result is user traffic that grows by the same bytes every minute, which shows
up as gigabytes used by a user who connected twice briefly.

How this fixes it:
- A report is one batch with an id (UsageInputOutputSchema.batch_id). The node
  stores the batch in flight in Redis and resends exactly that batch, unchanged,
  until the parent answers; new usage meanwhile collects in unsynced_usages for
  the next batch instead of being merged into one that may already be applied.
  After a successful answer the batch is dropped; unsynced_usages is no longer
  cleared wholesale, because it may hold usage for the next batch.
- The parent remembers the last applied batch id per node and, under the usage
  lock, skips a batch it already applied (it still answers normally, so the node
  gets its users and moves on). The id is marked after the usage was committed.
- batch_id is optional. An older node sends none and is treated as before, an
  older parent ignores the extra field, so mixed versions keep working (without
  the protection).

Logic lives in panel/usage_batch.py, with tests in tests/test_usage_batch.py._

* Fix(usage): keep the usage lock alive while it runs and release only your own. 
  _The usage update runs under a Redis lock ("lock-update-local-usage") that was set
with a fixed 60 second TTL and released with a plain DEL. A node's report to the
parent can take much longer than that: the client waits up to 90 seconds, and
retries on gateway errors and on other addresses make it longer still.

What went wrong:
- When the lock expired during a slow run, the next scheduler tick (or another
  worker; every granian worker has the scheduler) took the lock and started a
  second run while the first was still in progress. On a node both runs read the
  same unsent usage and sent it to the parent.
- When the first run then finished, its DEL removed the lock the second run was
  holding, letting a third run start on top of it.

How this fixes it:
- The lock value is now a random token owned by the run that took it.
- A small daemon thread renews the TTL every LOCK_TTL / 3 seconds while the
  locked function runs, so the lock only expires when the process died.
- The lock is released with a compare-and-delete Lua script, so a run can only
  delete its own lock.

The TTL stays 60 seconds, so a crashed process still frees the lock within a
minute._

* Merge branch 'dev' of github.com:hiddify/hiddifypanel into dev. 
  _Config health: the automatic checks being opt-in and the dashboard's Disable failing / Restore work together; the
API returns both `enabled` and `dead` / `disabled`.

Migrations: dev already has _v200 (built-in proxy names, str_config.value as TEXT), so the local ones move above it:
_v201 config_health_enable, _v202 warp_tos_accepted._

* Merge pull request #189 from Hiddify-Official/feat/pwa-new-icon. 
  _feat(pwa): new app icon for the installed panel and install guide_

* Feat(pwa): new app icon for the installed panel and its install guide. 
  _The installed app (phone home screen, computer) and the install guide use the
new "Hi" icon instead of hiddify-dark.png:
- manifest: 192 and 512 icons with rounded corners ("any") and an edge-to-edge
  512 one ("maskable") for the phone to cut to its own shape
- apple-touch-icon (180x180) on the admin and user pages; the guide's header
  shows it
- the guide's animation draws the same icon where it shows the app_

* Merge pull request #190 from Hiddify-Official/feat/proxy-name-casing. 
  _feat(proxy): built-in proxy names spelled like their protocols_

* Merge branch 'dev' into feat/proxy-name-casing. 

* Merge pull request #191 from Hiddify-Official/feat/settings-nav-live-icon. 
  _feat(settings): live icon of the current section in the phone chip bar_

* Feat(settings): live icon of the section on screen in the phone chip bar. 
  _On phones the Settings categories are a chip bar with no mouse, so the icons
never played their hover motion and the bar did not follow the page: scrolled
down to TUIC, the bar still showed its first chips.

- _icon-motion.scss: below 992px the active chip's icon plays its own motion
  (TUIC's plane flies, the gear turns, …), respecting reduced motion
- SettingsView: the chip bar scrolls sideways to keep the active chip in view
  (by rectangles, so the same in RTL; the page itself is not scrolled)_

* Merge pull request #193 from Hiddify-Official/feat/outbounds-touch-drag. 
  _feat(outbounds): drag handle on phones instead of the up/down buttons_

* Feat(outbounds): drag handle on phones instead of the up/down buttons. 
  _On phones the outbound rows had ↑/↓ buttons and no handle. The handle is now
shown there too (a larger touch target, above the number) and drives the
same smooth drag with a finger: the row lifts and follows it, the others
slide out of its way, and the page does not scroll while dragging. The ↑/↓
buttons are hidden on phones; desktop keeps both._

* Feat(outbounds): smooth, animated drag to reorder. 
  _Dragging an outbound by its handle used the browser's drag and drop: a faded
ghost, the other rows stood still and one line marked the drop place (above
the target even when the row went below it).

The handle now drives a pointer drag (mouse, pen or touch): the row lifts and
follows the pointer, the rows it passes slide out of its way, its number shows
the place it will take and an arrow which way it goes; on release it settles
into place and the order is saved, Escape puts it back. Near the window edge
the page scrolls. Rows move by transform only; the real order switches once,
with transitions off. The row entrance animation no longer holds its end
state, which overrode those transforms. Reduced motion is respected._

* Merge pull request #194 from Hiddify-Official/feat/scanner-operator-logo. 
  _feat(scanner): operator logos, Chinese and Russian operators_

* Feat(network): detect Chinese and Russian operators, with their logos. 
  _The panel only named Iranian operators; any other network was "unknown", so
the Scanner card showed no logo and the CDN IP field could not name them.

- maxmind: the main backbone ASes of China Telecom (CTC), China Unicom (CUC),
  China Mobile (CMC, with TieTong), China Broadnet (CBN), CERNET (CER),
  Rostelecom (RTK), MTS, MegaFon (MGF), Beeline (BLN), T2/Tele2 (T2R),
  ER-Telecom/Dom.ru (ERT) and TTK; any other AS by its registered organisation
  name, only for an address in that country (China Telecom alone has hundreds
  of provincial ASes; the same names abroad are other companies)
- the lookup cache gets its own namespace and a one-week expiry: answers
  cached for good before this would else stay "unknown"
- names in en/fa, local names in zh and ru; the admin's operator list
  (CDN IP field) has the new codes
- the 12 logos (Commons and Wikipedia vectors, CERNET's site, Broadnet's
  emblem cut from a Commons photo) with their sources in CREDITS.md

Checked against the panel's GeoLite2-ASN data: every China Telecom, Unicom,
Mobile, CERNET, Broadnet, Rostelecom, MTS, MegaFon, Beeline, T2, ER-Telecom
and TTK AS in China/Russia is named; MTS Bank, Toyota, Tele2 Sweden, MTS
Belarus, China Mobile Hong Kong and the Iranian operators are unchanged._

* Feat(scanner): the detected operator's logo on the network card. 
  _The Scanner's network card showed the same wifi icon for every operator. When
the panel recognises the operator, the card now shows its colour logo, for
all 15 operators the panel names: Hamrah-e Aval (MCI), Irancell (on the MTN
yellow), Rightel, Mokhaberat (TCI), Zirsakht (ITC), ParsOnline, Shatel,
Mobinnet, Asiatech, HiWEB, Respina, Afranet, Andishe Sabz, Pishgaman and
Zitel. Each logo is a 192x192 tile with its own background; an unknown
network or a VPN keeps the icon.

Sources (Wikimedia Commons, Wikipedia, the operators' own sites or their
Internet Archive copies), licenses and authors are in
assets/operators/CREDITS.md._

* Merge pull request #195 from Hiddify-Official/feat/mobile-menu-swipe. 
  _feat(admin): drag and swipe the phone menu open and closed_

* Feat(admin): drag the phone menu with a finger, swipe from the side to open it. 
  _On phones the menu only opened and closed with a tap on its tab, and a
sideways swipe from the left went back a page.

- The tab can be dragged: the menu slides with the finger (the mask dims with
  it), and on release opens or closes by how far it went or how fast it was
  flicked. A tap still toggles it.
- A sideways swipe starting on the start third of the page (the right in RTL)
  opens the menu the same way; a swipe back on the open menu or its mask
  closes it. A mostly vertical swipe stays a scroll; a swipe starting on a
  field, a slider, a drag handle or a row that can scroll sideways is left to
  it.
- overscroll-behavior-x: none on phones, so the browser's own sideways swipe
  (back/forward) does not fight it. The system edge-swipe of iOS cannot be
  taken over by a page._

* Merge pull request #199 from Dv2Corn/fix/str-config-text. 
  _fix(settings): settings longer than 3072 characters save on MariaDB_

* Fix(settings): settings longer than 3072 characters save on MariaDB. 
  _str_config.value was VARCHAR(3072). In strict mode (the default) MariaDB
rejects a longer value with error 1406 "Data too long for column value",
so saving failed with a 500: the spare REALITY SNIs after a scan (up to
300 names, about 10 KB) and a Full support text over 3072 characters (the
form allows 8192). SQLite does not enforce the length.

The column becomes TEXT in the model (new installs) and _v200 alters it on
existing databases with alter_column(), as _v156 did for user.extra_params.
_v199 is left to an open pull request._

* Merge pull request #196 from Hiddify-Official/fix/text-decoders-mobile. 
  _fix(utils): Text Decoders fits a phone; Latin digits in its fields_

* Fix(utils): Text Decoders fits a phone; links and fields keep Latin digits. 
  _On a phone the decoded link ran off the screen: a <fieldset> is as wide as
its widest content by default (here the long link name in its legend), and
PrimeVue's fieldset content is a grid item with the same default, so every
field, the parameter rows and their delete buttons went past the edge. In
Persian the technical values also showed Persian digits (port ۴۴۳, "%۲F" in
links) and right-to-left order (path "api/v1/stream/").

- SublinkEditor: min-width 0 on the fieldset and its content; a long link
  name is cut with "…" (from its own start in RTL); a narrower parameter
  name column on phones
- the fields (protocol, server, port, user, password, method, path,
  parameters) are LTR with Latin digits; the name follows its own text
- the link, Base64/URL and JSON boxes get a monospace font with Latin
  digits (PrimeVue's font rule had overridden the font-mono class)

The editor is also the Config Tester's subscription viewer, fixed with it._

* Merge pull request #197 from Hiddify-Official/feat/liquid-glass-theme. 
  _feat(admin): Liquid Glass theme with adjustable glass strength_

* Feat(admin): Liquid Glass theme, an iOS-like design with a glass strength. 
  _A third theme next to Hiddify and Smart Caddy, in the topbar's appearance
menu. Like the others it works in light and dark and is kept per browser;
it takes one of the Smart Caddy colors.

- layout.ts: theme 'liquid' (html.theme-liquid), the shared html.theme-glass
  of both glass themes, and the glass strength (admin_v2_glass, 0…100) as one
  CSS variable, --lg-strength. A change of theme, mode or color cross-fades
  (view transitions; not with reduced motion).
- _theme-liquid.scss, all under html.theme-liquid: one strength drives the
  see-through, blur, rim and depth of three levels: cards and the side menu
  (most glass), bars over content (denser), floating windows (dialogs,
  popovers, dropdowns, toasts: 86-98% opaque at any strength, and the page
  behind a dialog is blurred and dimmed, so text never mixes). Text, icons
  and controls are never see-through. Without backdrop-filter every surface
  is nearly solid.
- iOS design through PrimeVue's tokens, so every page follows: capsule
  fields, selects and buttons (soft rounded rectangle for multi-line
  fields), round checkboxes, iOS switches, segmented-control tabs, rounded
  dropdowns, menus, tables, tags, messages; the logo on a tile of the color.
- The background: slow waves of the color on two fixed layers (transform
  only); their colors are registered @property values, so a new color flows
  over. Still with prefers-reduced-motion.
- Appearance menu: the three themes as tiles with a preview, the colors for
  the glass themes, and an iOS volume-like "Glass" slider (left: most glass,
  right: most solid) with its percentage, live and kept.
- The floating parts that take a solid surface under Smart Caddy (chart and
  domain tips, node popovers, the menu tab) now key on theme-glass, and the
  color palettes also apply to Liquid Glass: Smart Caddy itself unchanged._

* Merge pull request #198 from Hiddify-Official/feat/footer-social-links. 
  _feat(admin): footer wordmark with Hiddify's website and channels_

* Feat(admin): footer logo with Hiddify's website and channels. 
  _The footer only showed the text "HiddifyManager". It is now a wordmark
("Hiddify" strong, "Manager" in the color; a translated name stays whole);
under the mouse a light sweeps across it from left to right (not while its
window is open). A click opens a small window above it with Hiddify's
website, GitHub, X, Telegram, YouTube and Instagram as round tiles in their
brand colors; each opens in a new tab (rel="noopener noreferrer"). The
channel under the mouse, and only it, comes alive: the globe turns, the cat
waves, the X spins, the plane flies off and back, the play button beats, the
camera flashes. The window closes on a link, a click outside or Escape (focus
back on the name); light, dark, RTL, phones and reduced motion.

The brand marks are inline SVG paths from Simple Icons 13.21.0 (CC0-1.0) in
shared/utils/brand-icons.ts: sharp at any size, no image files._

* Feat(proxy): built-in proxy names spelled like their protocols. 
  _Built-in proxy names are what users' apps show for each config, but they kept
the lowercase catalog words ("xhttp vless TLS H1") while the panel writes the
protocols as "VLess", "XHTTP", "gRPC"... Their words now take the same
spelling: "XHTTP VLess TLS H1", "gRPC VMess HC", "Hysteria 2 QUIC HC".

- preset_slots: preset_display_name spells the words; preset_tag_name keeps
  the original spelling, which the hiddify-core slugs and the DNS gateway
  server tags are still made from (no slug or tag changes)
- _v199 runs the preset sync, so existing servers rename their built-in
  proxies (a name an admin typed is kept)
- admin_v2: proxy names are shown as written, emoji included (📤 📥), as the
  users' apps show them, instead of as panel icons_

* Merge pull request #188 from Hiddify-Official/feat/health-disable-failing. 
  _feat(dashboard): Config Health turns off configs failing in both apps_

* Feat(dashboard): Config Health turns off configs that fail in both apps. 
  _Next to "Check now", two small buttons:
- Disable failing: after a confirmation that lists them, turns off the
  custom proxies whose every config failed both as the Xray apps and as the
  Hiddify app get them, in the last check. A proxy with one working config
  in either app stays on, and nothing is offered when an app could not be
  tested. The count is on the button; the Apply notice follows.
- Restore: turns them back on.
On phones both show only their icon and count.

Each check now also keeps, per app, every custom proxy's status (down /
partial / up, from config_tester_proxies.health over all tested configs, not
the shortened failed list). GET config-health/ adds `dead`, `dead_known` and
`disabled`; POST config-health/disable/ and config-health/restore/ reuse the
config tester's disable/restore and its record, so either page's Restore
brings back what either turned off._

* Merge pull request #187 from Hiddify-Official/feat/menu-active-box. 
  _feat(menu): the open page's menu item has a box without hovering_

* Feat(menu): the open page's menu item has a box without hovering. 
  _The sidebar showed the current page only as bold coloured text; the box
appeared only on hover. The active item now has a soft box in the panel
colour (tint and a 1px ring), a little stronger on hover. Parents of the
open page (e.g. Tools) stay plain._

* Merge pull request #183 from Hiddify-Official/fix/admin-number-stepper. 
  _fix(admins): − / + and typing in limit fields work on phones_

* Fix(admins): limit fields' − and + react to every tap on phones, typing works. 
  _The admin form's limit fields used PrimeVue's InputNumber. Its buttons step on
mousedown and focus the input first, so on a phone the keyboard opens, the
dialog resizes and the tap misses: the buttons needed several taps. It types
through keypress, which Android keyboards don't send, so typed digits mixed
with its formatting and only counted on blur.

NumberStepper (shared): the buttons step on click without taking the focus,
the field is a plain text input with a numeric keyboard that reads what was
typed on every change (Persian and Arabic digits too, decimals up to the
field's precision) and clamps to the allowed range on blur._

* Merge pull request #184 from Hiddify-Official/fix/pwa-dialog-small-screens. 
  _fix(pwa): install guide keeps "Got it" in view on small screens_

* Fix(pwa): install guide keeps "Got it" in view on small screens. 
  _The dialog's content had overflow hidden and no height of its own: on a short
window the bottom (Got it) or, once the button took the focus, the top was cut
off with no way to scroll to it. On phones the sheet was 92vh, which includes
the part under the browser's bars.

Only the guide scrolls now; the buttons stay at the bottom, with a line over
them while there is more above. The dialog is sized to the visible screen
(dvh). Phones and short screens drop the line under the title, and below
640px of height the app icon and the animated scene are smaller._

* Merge pull request #185 from Hiddify-Official/fix/settings-nav-active. 
  _fix(settings): the category picked in the menu stays highlighted_

* Fix(settings): the category picked in the menu stays highlighted. 
  _Clicking a category (e.g. TUIC) often highlighted another one (Advanced
Settings). The IntersectionObserver callback only gets the cards whose
visibility just changed, and the smooth scroll to the clicked card passes
others, so the last card to cross the band won; a card near the end of the
page can't reach the band at all.

The spy now reads the scroll position: the highlighted category is the last
card whose top passed the line under the top bar (or the last card at the
bottom of the page). A category picked in the menu or by a deep link stays
highlighted until the admin scrolls, clicks in the page or uses the keys._

* Merge pull request #186 from Hiddify-Official/feat/users-page-scrubber. 
  _feat(users): drag through the pages of the users list_

* Feat(users): drag through the pages of the users list. 
  _The users list's paginator (a row of PrimeVue links on desktop, only ‹ x–y ›
on phones) becomes PageScrubber, a shared component:
- a bar to drag through the pages: far left the first page, far right the
  last, in every language; a bubble shows the page while dragging; « and »
  at its ends; arrow, Home and End keys work on it. On a wide list it is a
  quarter of the window, between the report and Previous / Next.
- the page numbers around the current one (1 2 3 … 24)
- Previous / Next and a "page [n] of N" field to jump to (Persian digits too)
- "Showing x–y of N"
On a narrow list the parts stack (bar, numbers, then Previous · page · Next).

Dragging the bar keeps the pager where it is on screen: the phone list
measures its cards while they are swapped, which made the browser drop the
scroll to the top on every page change. On phones, Previous / Next, a page
number or a typed page scroll to the top of the page.

The table no longer paginates itself: it gets the current page's rows, as
the phone cards already did, so both use the same pager._

* Feat(warp): WARP routes only after an admin accepts Cloudflare's terms. 
  _- warp_tos_accepted (hidden), off; _v200 keeps it off on upgrades. Traffic goes through WARP only when WARP is on and
  the terms are accepted; turning WARP on in the settings is refused until then.
- admin_v2: a terms dialog in Outbounds and Settings (POST outbounds/warp-terms/), and a banner while WARP is on but
  the terms are not accepted. GET settings/ returns warp_tos_accepted with the categories.
- a parent hands its acceptance to its nodes on the WARP outbound row; an older parent leaves the node alone.
- empty translation entries for openvpn_certificate and openvpn_private_key._

* Feat(admin): add a QR code tool. 
  _Tools > QR code: scan a code from the camera or an image (zxing-wasm) and make one from a link, in the plain or the
Hiddify style. Scanned subscription links open in Text decoders through the navigation state, not the address._

* Ci: remove the Ninja i18n workflow. 
  _Its trigger was commented out, so it never ran._

* Fix(config-health): make the automatic checks opt-in and lighter. 
  _Each check started a core for every config of the subscription and connected through it to the server, after every
start and every 6 hours: hundreds of connections in a few minutes, which hosting providers took for a flood and
suspended servers for (hiddify/Hiddify-Manager#5672).

- new setting config_health_enable (Settings > General), off; _v199 sets it off on existing panels. The scheduled,
  start-up and follow-up checks run only when it is on; "Check now" always works, and the dashboard card says the
  automatic checks are off.
- Xray's "Auto" balancer is not started (its observatory probed every config at once and its result was not used).
- the retry runs only the configs that failed, not the whole subscription (config_tester.run takes a `select` filter).
- one request per config and 4 configs at a time (were 2 and 8)._



## v14.2.0 (2026-11-06)

#### New

* Add shadowtls similar to all sni proxies. 

* Add advanced ip/sni scanner. 

#### Other

* Feat(openvpn): add OpenVPN UDP and TCP, served by hiddify-core. 
  _Two proxies, "OpenVPN UDP" and "OpenVPN TCP": hiddify-core openvpn-server
endpoints on their own ports (one network per endpoint, separate subnets
10.93.0.0/16 and 10.94.0.0/16), listening on all addresses. Users log in
with their uuid; with no user the endpoint is not served. A self-signed
server certificate (migration _v198) is pinned in the client configs.

Clients: an openvpn-client endpoint for the Hiddify app 5+ / sing-box
1.14+, and a .ovpn for the OpenVPN apps from /openvpn (new client core
"openvpn", listed on the user page). No share link.

One switch, openvpn_enable (off by default). The WireGuard endpoint
builder and the .conf download are shared with OpenVPN.

Not counted per user yet: hiddify-core does not tag the connections of
an OpenVPN user, so usage stats and limits do not see them._

* Feat(translations): update template translations and add new branding text fields. 

* Feat(store): implement folder locking for certificate operations and add unused certificate removal functionality. 
  _- Introduced a context manager for exclusive folder locking during certificate writes and removals to prevent conflicts.
- Updated `write_files` and `remove_files` functions to utilize the new locking mechanism.
- Added `names_in_use` and `remove_unused` functions to manage and clean up unused certificates based on domain usage.
- Enhanced `export_all` to call `remove_unused` for better certificate management._

* Feat(admins): filter the admins page by any permission. 
  _The permission filter lists every permission of the edit dialog (with the
same icons) and "No special permissions", instead of only can / can't add
sub-admins._

* Merge. 

* Merge pull request #181 from Hiddify-Official/feat/support-full-text. 
  _feat(branding): support box Lite and Full texts, templates with both_

* Feat(branding): support box Lite and Full texts, templates with both. 
  _The support box gets a Full text (branding_freetext_full, _v197), shown by
"Read More" on the user page; branding_freetext is the Lite text shown in the
box. Empty Full: Read More shows the Lite text when it does not fit, as before.

Admin: the HTML editor edits both (Lite / Full tabs; the toolset switch is now
Basic tools / All tools), View previews both, and every template has a short
Lite version and a Full one; Insert / Replace fills both texts. The user API
sends admin_message_full_html (not the panel's when an admin overrides only
the Lite text)._

* Feat(admins): each admin counts its users' traffic with a reset period like users. 
  _The usage update groups the users' traffic by admin, walks up the admin tree
once per admin and adds it to the admins and all their parents in a single
UPDATE. Admins get a reset period (daily/weekly/monthly/never) and a reset
button in admin_v2; the traffic limit uses this counter. Migration _v196
starts each counter from its users' current usage._

* Fix(mieru): give Hiddify <= 5.5.5 the server IP, it fails when it cannot resolve the name. 

* Merge branch 'dev' of github.com:hiddify/hiddifypanel into dev. 

* Merge pull request #180 from Hiddify-Official/feat/html-editor-templates. 
  _feat(admin_v2): templates button in HTML editor top bar, 14 more designs_

* Feat(admin_v2): templates button in the HTML editor's top bar, 14 more designs. 
  _The template gallery opens from a button next to Preview / Source, in Lite and
Full and in Source mode too (Insert appends to the code there), instead of a
Full-only toolbar icon. The gallery is grouped (contact, news, sales, guides)
and has 14 new support box designs, all within the setting's length limit and
kept unchanged by the panel's HTML sanitizer._

* Merge pull request #179 from Hiddify-Official/fix/meter-ltr. 
  _fix(admin_v2): fill usage bars left to right in RTL languages_

* Fix(admin_v2): fill usage bars left to right in RTL languages. 

* Merge pull request #178 from Dv2Corn/fix/telegram-renew-active-limit. 
  _fix(telegram): Renew no longer turns a user on past max active users_

* Fix(telegram): Renew no longer turns a user on past max active users. 
  _The bot user card checks max_active_users on "Turn on", but "Renew" sets enable as well and skipped
the check, so an admin at the limit could turn disabled users on again by renewing them. Renew now
asks can_activate_more_users() when the user is disabled; renewing a user that is already on is not
one more active user and stays allowed._

* Merge pull request #176 from Dv2Corn/fix/http-switch-non-http-protos. 
  _fix(proxies): turning off HTTP connections no longer drops Shadowsocks 2022 and Mieru_

* Fix(proxies): turning off HTTP connections no longer drops Shadowsocks 2022 and Mieru. 
  _Shadowsocks 2022, Mieru and the DNS tunnels are stored with tls_layer
"http", which for them only means "no TLS layer". parent_enable_keys()
mapped every tls_layer "http" to http_proxy_enable, so turning off
"Allow HTTP Connection" also turned these proxies off. The switch now
applies to them only through their own protocol switches; plain HTTP
proxies (VLESS/VMess/Trojan over WS, HTTPUpgrade, raw HTTP, gRPC,
xHTTP, raw TCP without TLS) still follow it.

Fixes hiddify/Hiddify-Manager#5666_

* Merge pull request #175 from ShawnJim/fix/foxray-subscription-privacy. 
  _fix(user): avoid external HTTPS helpers for Foxray subscriptions_

* Fix(user): avoid external HTTPS helpers for Foxray subscriptions. 

* Merge pull request #174 from miladosos/fix/validate-non-json-server-templates. 
  _fix(templates): overrides of text server templates can be saved_

* Fix(templates): overrides of text server templates can be saved. 
  _The template editor validates a base config before saving it, and the
validator parsed the rendered output of every server base config except
wireguard as JSON5. Seven server templates are plain text: haproxy (HAProxy
config), rust-rpxy-l4 and telemt (TOML), wireguard (.conf), firewall (bash)
and ip_scanner / sni_scanner (Python). Their overrides could not be saved,
even unchanged: validation failed with json5_parse.

- TEXT_SERVER_BASE_CORES (next to BASE_CONFIG_MATRIX) lists them. Validation
  renders them (Jinja errors are still reported) without parsing JSON, and the
  two previews render them as text, as TextServerDriver does when it writes
  the config.
- Validation and preview give these templates the variables they get outside
  the editor: the text driver's extra_jinja (the firewall's public_ports, the
  HAProxy cert dir, the WireGuard NICs) and sample values for the scanner
  scripts. Without them the built-in firewall and ip_scanner templates failed
  with "'public_ports' is undefined" / "'size' is undefined".

Tests render every built-in text server template through the validator and
check that the list stays in sync with the TextServerDriver cores._

* Merge pull request #173 from Hiddify-Official/fix/dashboard-network-rate. 
  _fix(dashboard): network chart shows the server's real upload/download_

* Fix(dashboard): network chart shows the server's real upload/download. 
  _The chart summed every interface. HAProxy, Xray and Hiddify Core pass
each connection to each other over loopback, so the same bytes counted
in both directions (and WARP/WireGuard tunnels counted traffic a second
time): a 40 Mb/s proxied download showed about 40 Mb/s of upload and
85 Mb/s of download, a symmetric chart.

- network_metrics() (and the legacy system_stats()) count only the
  server's physical interfaces (those with a device), or every
  interface but loopback and tunnels when there is none.
- Node health keeps upload in the top half and download in the bottom
  half, with the same range on both sides (the peak rounded to
  1/2/5 x 10^n bits/s, so zero is in the middle and ticks are round).
- Every node in its own colour (upload solid, download dashed; several
  nodes stack per side), labels on the two halves, and a legend with
  each node's current rates (a dash for a node the panel cannot reach).
- The nodes page's live chart uses the node's colour._

* Feat(users): implement functionality to place newly created users at the top or end of the list, enhancing user management experience. 

* Refactor(decoy_upstream): update server configuration for improved SSL handling and backup server setup. 

* Refactor(config_health): enhance config failure notification logic and add retry mechanism. 

* Fix(domain): do not resolve ip if domain is entered in forced cdn ip. 

* Fix(sublink): send fragment= again for apps that do not read FinalMask. 
  _Karing, older v2rayNG and Hiddify <= 5.0.0 only read the share-link
fragment=<length>,<delay>,<packets>; since FinalMask they got only fm= and
imported no fragment. Build it from the domain's finalmask (first length and
delay); Hiddify > 5.0.0 reads fm and does not get it._

* Refactor(configs_api): update Full Xray subscription URL to include ASN parameter and simplify logic. 

* Refactor(apply_users): move quick_apply_users to hutils and update references. 

* Fix(user_driver): handle connection errors gracefully when checking enabled users. 

* Fix(translations): restore "define_mode" key in multiple language files. 

* Fix(telemt): IPv6 public_addr in brackets. 
  _A domain on an IPv6 address gave public_addr = "2001:db8::1:443", which telemt cannot split into
address and port, and the Telegram proxy service failed. Now "[2001:db8::1]:443"._

* Fix(settings): support box title and button text are not ports. 
  _"port" in the key matched "support": branding_support_title and branding_support_more got the
port-number pattern, so typing any text in the HTML editor failed with only "fix the marked fields".
Only keys ending in _port/_ports are ports now; errors of a field edited in another field's editor
show on that owner's row._

* Feat(panel): RAM notice for the proxy cores' users, more panel workers on a big parent panel. 
  _xray and hiddify-core keep every user in every inbound (40 000 users x 106 inbounds = 4 million entries,
~200 MB configs), and a server with too little RAM gets them killed by the OOM killer again and again.

- The server config dump counts the user entries of xray / hiddify-core (generated/core-load.json; the user
  list is dumped again on every change). The admin notices estimate the RAM: 3 KB per entry, 50 MB per core,
  and the panel at 200 MB + 2 MB per user (up to 1 GB). A warning from 50% of the RAM, an error (also as a
  toast) from 80%: reduce the active protocols, disable users or add RAM.
- `panel-workers` CLI: granian workers for hiddify-panel.service, one per 10 000 users on a parent panel
  (at most the CPUs, 2 GB of RAM each, and 4); 1 everywhere else.
- With several workers each one has the scheduler: the backup and the Telegram expiry notices run in one
  of them (run_once: a redis lock kept for an hour).
- The admin notices count the users instead of loading them all._

* Perf(users): users page and bulk actions stay fast with thousands of users. 
  _Users page (admin_v2):
- "All" mounts only the rows / cards on screen (windowed list on phones, PrimeVue virtual scroller on the table);
  selection is a Set lookup instead of a scan per row.
- Bulk actions show what is running: the clicked button spins, the others wait, the bar says "Working on N users…".

Bulk create, up to 10 000 users:
- Limits checked once for the batch, against the chosen owner and the admins above it; owner resolved once.
- WireGuard keys made in-process (three `wg` processes per user before); tags saved with the users.
- New users go to the cores in one batch per driver: xray calls pipelined, the generated config read once,
  one Redis save for SSH. Batches over 100 run after the response; the dialog says links work in a minute or two.

Bulk enable / disable / resets / add days / add limits / delete / tag:
- One UPDATE per chunk in SQL and the users read back in a few queries (one query per user before).
- Active ceiling checked once; cores updated in one pipelined batch, in the background for big ones. A user
  changed again while a batch runs gets that last change once it ends.
- Bulk tag is set-wise (visibility, validation, delete, insert once).
- Telegram message to a big selection sends the ids in the body (broadcast/selection/), not the URL.

User forms:
- Add many users uses the same cards, reset period picker, quick picks, time line and collapsible Advanced
  as the single-user form (shared components in users/components/package/).
- A wrong field or a server error scrolls into view and takes the focus; missing common.done translation added._

* Feat(settings): fix port conflict detection for configuration settings. 

* Fix(haproxy): no https redirect loop behind a CDN that ends TLS and comes in on :80. 
  _Cloudflare Flexible SSL sends the request to :80 with X-Forwarded-Proto: https / cf-visitor; the 301 to https came
back on :80 again (ERR_TOO_MANY_REDIRECTS on the panel and the subscription links)._

* Fix(sublink): configs that failed on xray 26.10 / hiddify-core 5.3 / mihomo 1.19.32; config tester uses the installed cores' versions. 
  _- hiddify-core: VMess cipher named (aes-128-gcm); its "auto" is a cipher id xray 26.10 rejects
- Mihomo: REALITY with X25519MLKEM768 (xray 26.10 refuses the X25519-only hello)
- Mihomo: xhttp download-settings say tls:false and their ALPN instead of taking the upload's
- Mihomo: no trojan over http/h2 (unsupported) and no H1 upload with the download on another server
- config tester and health check: user agents from the installed xray, hiddify-core and mihomo (GET config-tester/apps/)_

* Feat(haproxy): decoy requests go to https first; a Host other than the TLS SNI gets 421. 
  _Only requests no proxy map took (default_decoy): cleartext is redirected to https (301); over TLS, a Host that differs
from the SNI (domain fronting) gets the plain "421 Misdirected Request" other servers answer, instead of the decoy.
The SNI of TLS ended on an earlier hop (:901) comes along as the PROXY v2 authority._

* Feat(telegram): serve the Telegram web proxy domains with telemt's wildcard hosts. 
  _telemt 3.5.16 (allow_wildcard_hosts): the domains on the main public IP share one "*" vhost group, so every user's profile is kept once instead of once per domain (6 domains x 137 users: 1 group instead of 6). A domain on another public IP keeps an exact group (public_addr is fixed per group). Unknown hosts get the decoy in the outer layer, before telemt._

* Feat(branding): support box title/button settings and private config names for domains without an alias. 
  _Support box (user page): its title and View More button can be renamed or hidden, edited in the support text's HTML
editor (branding_support_title/_more and their _show switches, _v194). user_front follows them.

Config names: a domain without an alias is no longer named by its domain in config names, profile titles and
subscription names (domain_label_mode, Settings > General, _v195):
- private (default): its kind and a keyed-hash code, e.g. '☁️ CDN K7Q', which does not reveal the name
- masked: e.g. '⚡ h*y.com', '⚡ 94.*.*.*'
- full: the domain name, as before_

* Refactor(admin): remove the deprecated Flask-Admin pages; admin is admin_v2 only. 
  _admin_v2 (Vue) and its API replaced every legacy page, which were only reachable in
debug mode. Removed:
- panel/admin: the Flask-Admin model views (users, domains, admins, nodes), the old
  Dashboard, Settings, Proxies, Quick setup, Backup, Actions, Terminal and AdminLTE glue,
  and their templates; templates/ admin layouts and hiddify-flask-admin.
- panel/commercial: ProxyDetailsAdmin, ParentDomainAdmin and their templates; the
  admin_prehook event; panel/admin_2.py.
- hiddify.reinstall_action / check_need_reset and hutils.flask.flash_config_success
  (only the old pages used them); the legacy endpoint map in hurl_for.
- flask-admin and flask-adminlte3 dependencies.

Kept and moved: the settings form the admin API builds on, from
panel/admin/SettingAdmin.py to panel/settings_form.py. /admin/ redirects to admin_v2;
a node without a base URL links to admin_v2's Nodes page._

* Refactor(i18n): read Flask translations from translations.i18n JSON, drop .po/.mo. 
  _The .po files were generated from translations.i18n/<lang>.json (flattened keys as
msgids) and compiled to .mo, so they were a stale copy of the JSON (en and my
already differed). Flask-Babel now reads the JSON directly through a JsonDomain:
every _() / gettext / lazy_gettext call in Python and Jinja works as before, with
English as the fallback for keys a language lacks.

- hiddifypanel/json_translations.py: JSON catalogs, loaded once per process.
- remove hiddifypanel/translations (*.po, *.mo) and scripts/auto_translate.py.
- update_translations.sh: only adds new msgids to the JSON files.

scripts/translate_utils.py keeps only update-json (new msgids from pybabel extract into the JSON files); its .po conversion commands are gone._

* Merge pull request #167 from Hiddify-Official/fix/vless-encryption-guard. 
  _# Conflicts:
#	hiddifypanel/translations/en/LC_MESSAGES/messages.mo
#	hiddifypanel/translations/fa/LC_MESSAGES/messages.mo
#	hiddifypanel/translations/my/LC_MESSAGES/messages.mo
#	hiddifypanel/translations/pt/LC_MESSAGES/messages.mo
#	hiddifypanel/translations/ru/LC_MESSAGES/messages.mo
#	hiddifypanel/translations/zh/LC_MESSAGES/messages.mo_

* Fix(proxies): a wrong VLESS encryption key no longer stops Xray. 
  _Xray refuses to start on a VLESS "decryption" it can't parse, and stays
"activating" until the setting is cleared. The panel saved both
settings as free text and put the decryption into every VLESS inbound.

- Settings: VLESS encryption/decryption are checked as Xray parses them
  (method, mode, ticket time or 0rtt/1rtt, padding, key sizes) and must
  come from the same `xray vlessenc` output (the client key is derived
  from the server key), or both be empty. Pasted spaces are trimmed.
  The error says what to paste; the descriptions explain both fields.
- Configs: a stored value that fails those checks (older panel, backup,
  node sync) turns VLESS encryption off for the server and the clients,
  with a warning in the log, instead of breaking Xray._

* Merge pull request #169 from Hiddify-Official/feat/html-editor. 
  _# Conflicts:
#	hiddifypanel/admin_v2/src/features/settings/components/SettingFieldRow.vue
#	hiddifypanel/translations/en/LC_MESSAGES/messages.mo
#	hiddifypanel/translations/fa/LC_MESSAGES/messages.mo
#	hiddifypanel/translations/my/LC_MESSAGES/messages.mo
#	hiddifypanel/translations/ru/LC_MESSAGES/messages.mo_

* Feat(admin): advanced tools in the HTML editor's Full mode. 
  _So nothing needs an outside site, Full mode adds:

- Template gallery: ten ready-made support box designs (banner,
  contacts, announcement, status messages, FAQ, two columns, plan
  card, support hours, social buttons, getting started) with a live
  preview, inserted at the caret or replacing the text.
- Block style: background (colour, or a gradient with its angle), text
  colour, padding, space below, corners, border, shadow, full width
  and line height of the block at the caret, or of its parent.
- Element path under the text (body > div > ul > li): picking an
  element selects it for the block style.
- Table tools while the caret is in a table: rows above/below, columns
  before/after, delete row, column or table.
- Find & replace with a match count (Source: the code editor's own).
- Clean up code: empty and attribute-less spans, empty styles, class
  and data attributes, trailing empty lines.
- Copy the HTML, download it as a file, open an HTML file.
- FAQ item (details/summary).

Escape no longer closes the editor (it closed it from a tool's popup,
losing what was not applied); the window closes with Cancel or ×._

* Feat(admin): built-in HTML editor for the users' support box. 
  _Settings > Customizing User Page > Support Section Text linked to an
outside site to write HTML. The row now has two buttons:

- View: the box as users see it (their page's look, read only).
- HTML Editor: a window with the panel's own editor.
  - Preview / Source: edit the text in place as it looks on the user
    page, or its HTML in the code editor (highlighting, tag
    completion, Format code, line wrap).
  - Lite / Full (remembered): everyday tools, or all of them:
    paragraph and heading formats, font and size, bold to
    superscript, text colour and highlight, alignment, lists, indent,
    quote, link, image, table, divider, box, button, emoji, special
    characters, text direction.
  - OK / Apply / Cancel, a length counter against the setting's limit.

The text is edited in a sandboxed iframe (nothing in it runs). The
user page resets headings, lists and links to plain text, so the frame
does too and the tools write inline styles for them: what looks right
in the editor looks the same on the user page. Enter after a styled
block starts a plain line instead of repeating the block._

* Fix(admin): Monaco language workers load; ship the HTML service. 
  _Monaco's workers got "<ui>/monaco/<hash>/vs/" as their base URL, but
their modules are named "vs/…", so a language worker was looked up
under vs/vs/ and failed (an [object Event] page error). The base is now
the directory above vs/.

The HTML language service (480 KB, loaded only when an HTML editor
opens) is copied with the rest of the prebuilt Monaco, for formatting
and tag completion in the support box's HTML editor. JSON, CSS and
TypeScript services stay out._

* Merge pull request #170 from Hiddify-Official/feat/torrent-block-toggle. 
  _# Conflicts:
#	hiddifypanel/panel/init_db.py
#	hiddifypanel/translations/en/LC_MESSAGES/messages.mo
#	hiddifypanel/translations/fa/LC_MESSAGES/messages.mo
#	hiddifypanel/translations/my/LC_MESSAGES/messages.mo
#	hiddifypanel/translations/pt/LC_MESSAGES/messages.mo
#	hiddifypanel/translations/ru/LC_MESSAGES/messages.mo
#	hiddifypanel/translations/zh/LC_MESSAGES/messages.mo_

* Feat(settings): Block BitTorrent switch that works on every core. 
  _Settings > General had a torrent_block setting that did nothing: its
row was never created (so the switch was not shown), Xray always
blocked BitTorrent and Hiddify Core never did.

- _v192 creates the setting, on by default (as Xray behaved).
- Xray: the bittorrent -> blackhole rule only when it is on.
- Hiddify Core: after the sniff action, BitTorrent is rejected when it
  is on (sing-box recognizes the handshake on any port).
- The switch is an advanced General setting (not essential), with a
  label and description saying what it does, in all languages._

* Merge pull request #172 from Hiddify-Official/feat/config-tester-disable-down. 
  _# Conflicts:
#	hiddifypanel/admin_v2/src/features/config-tester/views/ConfigTesterView.vue
#	hiddifypanel/panel/init_db.py_

* Feat(config-tester): turn off the panel's down configs, restore them later. 
  _After a test, a new card shows this panel's own configs (custom
proxies) the test reached. A tested config belongs to the proxy whose
name its name starts with (the longest one; client/tag.j2 names
configs after their proxy, then the domain…).

- Down (every tested link of the proxy failed) are picked to be turned
  off; partly down ones (some domains still work) stay on unless the
  admin picks them; working ones are listed on request.
- "Turn off" asks first, turns the picked proxies off and shows the
  Apply notice.
- What the tester turned off is kept (config_tester_disabled, a hidden
  config: [[proxy id, time], ...]) and shown at the top of the page
  with "Restore all", which turns them back on only when the admin
  asks. One that cannot be on now (its protocol is off in Settings)
  stays in the list.
- API: GET/POST config-tester/proxies/, POST .../disable/,
  POST .../restore/ (super admins).
- _v193 adds the config key (the str_config key enum only grows when a
  migration runs)._

* Merge pull request #143 from Hiddify-Official/fix/warp-title-plus. 
  _# Conflicts:
#	hiddifypanel/translations/en/LC_MESSAGES/messages.mo
#	hiddifypanel/translations/my/LC_MESSAGES/messages.mo
#	hiddifypanel/translations/pt/LC_MESSAGES/messages.mo
#	hiddifypanel/translations/ru/LC_MESSAGES/messages.mo
#	hiddifypanel/translations/zh/LC_MESSAGES/messages.mo_

* Fix(admin): the WARP settings section is called "WARP", without "➕" 
  _The section's title (config.warp.label) read "WARP➕" in the Settings list
and on its card. The Persian title was already "WARP". The JSON sources
and the server's .po/.mo catalogs get the same text; the catalogs were
recompiled with pybabel (only that entry and the header change)._

* Merge pull request #142 from Hiddify-Official/feat/icon-hover-motion. 
  _# Conflicts:
#	hiddifypanel/admin_v2/src/assets/sakai/layout/layout.scss_

* Feat(admin): the side menu and Settings icons come alive on hover. 
  _The icons only wobbled a little on hover. Now the icon stays as it is and
only its glyph moves, each in its own way: the house hops, the users nod,
the plane flies off and comes back, the gear turns, the heart beats, the
lock shakes, the cloud drifts, ... (_icon-motion.scss, one map of icon ->
keyframes for both places). The motion repeats with a short rest while the
mouse stays on the item; the icon clips the glyph, so a glyph that leaves
comes back in cleanly. Nothing moves on touch or with reduced motion._

* Merge pull request #139 from Hiddify-Official/feat/dashboard-node-flags. 
  _# Conflicts:
#	hiddifypanel/admin_v2/src/features/dashboard/components/NodeHealthCard.vue
#	hiddifypanel/admin_v2/src/features/nodes/views/NodesView.vue_

* Feat(admin): country flags beside the nodes in the dashboard's Node health. 
  _Each node's country comes from its address, by the same cached MaxMind
lookup as the Nodes page; This server's from its own public IP. The flag
shows before the name in the legend, the table and the phone cards; the
flag helpers move to shared/utils/country.ts for both pages._

* Merge branch 'dev' of github.com:hiddify/hiddifypanel into dev. 

* Merge pull request #164 from Hiddify-Official/fix/api-docs-mobile. 
  _fix(api-docs): readable API page on phones_

* Fix(api-docs): readable API page on phones. 
  _The API page (Stoplight Elements, APIFlask's docs) always used its
"sidebar" layout: on a phone the sidebar took the screen and squeezed the
content into a narrow column. Elements' "responsive" layout keeps the
sidebar on wide screens and turns it into a menu (☰) on narrow ones._

* Merge pull request #146 from Hiddify-Official/fix/node-health-rows. 
  _fix(dashboard): Node health rows the same height, names centred_

* Fix(dashboard): Node health rows the same height, each name in the middle. 
  _A node without a known host name (an offline one) had no second line under
its name, so its row was shorter, and in the others the two lines put the
name above the middle. The host name now follows the name on the same line,
small and grey, so every row is one line with the name centred; the Offline
tag is no taller than a line of text._

* Merge pull request #145 from Hiddify-Official/fix/domain-cert-errors. 
  _fix(domains): no "none" domains; certificate errors in plain words_

* Feat(domains): a failed certificate opens with "Show more" 
  _The certificate error took a block under the row, so a row with an error
was twice as tall as the others. The badge line now says why in a few words
("Not a real domain name") with a "Show more" button; the full story
(plain-words lead, numbered steps, Try again, the CA's message under
Technical details) unfolds under the row in a card of its own, and "Show
less" closes it. Closed, the row keeps the height of the others (#152)._

* Fix(domains): no "none" domains when the IPv4 is not found; plain-words certificate errors. 
  _The first setup named the server's default domains after
str(get_ip_str(4)): on a server whose public IPv4 was not found (an
IPv6-only server) that made "none" and "none.sslip.io", which never get a
certificate, so the Domains page showed "Certificate failed" on them for
good.

- _default_domains(): the IPv4 and <IPv4>.sslip.io, else <IPv6>.sslip.io,
  else none at all.
- _v191 removes "none" and "none.sslip.io"; only when they are the
  server's only domains do its default names take their place first.
- Domains page: a failed certificate says why in plain words (not a real
  domain name, the domain does not point here, port 80 closed, CAA record,
  the CA did not answer, other) with numbered steps; the CA's message is
  under Technical details._

* Merge pull request #140 from Hiddify-Official/fix/note-peek-flash. 
  _fix(users): note sheet no longer flashes at the page's top left_

* Fix(users): the note sheet no longer jumps to the page's top left. 
  _Moving the mouse over the sheet's border or arrow left the inner box that
listened for it, so the sheet started closing. Coming back reopened it
anchored to that inner box, which is removed once the sheet closes, so it
showed at the page's top left corner for a moment and closed.

The sheet now always opens under the note's words, and the whole popover
(border and arrow included) counts as being on the sheet._

* Merge branch 'dev' of github.com:hiddify/hiddifypanel into dev. 

* Merge pull request #171 from DrvpnTM/fix/infer-proto-missing. 
  _fix(custom-proxy): restore infer_proto_from_categories_

* Fix(custom-proxy): restore infer_proto_from_categories. 
  _The helper was removed in acb69a0d but is still called when a proxy is
saved without a protocol, so saving a new proxy failed with NameError._

* Merge pull request #168 from Hiddify-Official/feat/support-box-html5. 
  _feat(admin): HTML5 and inline styles in the users' support box_

* Fix(admin): keep logical CSS properties in the support box. 
  _margin/padding/border-inline-start and the like (what right-to-left
pages use) and the list-style shorthand were dropped on save._

* Feat(admin): HTML5 and inline styles in the users' support box. 
  _The support box text (branding_freetext) was cleaned with bleach's
defaults: div, section, table and the like were escaped and shown as
code on the user page, and style/align and other attributes were
dropped. The per-admin user page setting was not cleaned at all.

Both now go through hutils/user_html.clean_user_html:
- HTML5 text, block, list, table and media tags with their usual
  attributes (style, align, dir, class, colspan, width…);
- inline CSS limited to text, colour, box, flex and grid properties,
  with no positioning and no url(), so the box can't cover the page or
  load anything;
- no scripts, handlers, frames, forms or <style> (removed with their
  content); links and media only over http(s), mailto, tel and tg.

bleach's CSS sanitizer needs tinycss2: bleach[css]._

* Merge pull request #166 from Hiddify-Official/fix/responsive-audit. 
  _fix(admin): responsive and glass-theme layout fixes across the panel_

* Fix(admin): only the logo in the top bar when the name does not fit. 
  _On a narrow phone the panel's name ended in "…" (HiddifyM…). It is now
shown only when it fits whole: the top bar measures it on every resize
(and language change) and hides the name and version otherwise, so only
the logo stays. The link keeps the name as its aria-label._

* Fix(admin): glass theme bars cover what scrolls beneath them. 
  _Sticky and fixed bars took the thin card glass (52-58 % opaque, most
with no blur), so the page passing under them showed through their
buttons: the Settings save bar, the Send message bar, the user dialog's
actions, the SSH commands panel, and on phones the settings categories
and Quick setup's buttons. One mixin (caddy-bar: the strong glass with
a blur, like the top bar) is used by all of them; the default theme and
the glass cards are unchanged._

* Fix(admin): top bar actions stay on screen on small phones. 
  _At 320 px the top bar (2rem padding, menu button, logo, four 2.5rem
actions 1rem apart) was wider than the screen: the last actions were cut
off on every page. On phones the logo now gives way (its title ends in
"…"), and up to 420 px the padding and the gaps are smaller._

* Fix(admin): switches keep their size next to long labels. 
  _On phones a ToggleSwitch in a flex row with a long label (Send message's
"Add each user's usage and buttons", the domain dialog's Resolve IP and
ECH) was shrunk by flex: the track got narrower than the knob, which
stuck out of it when on. One global rule keeps every switch at its size
(flex-shrink: 0), so no other row can do it again._

* Merge pull request #165 from Hiddify-Official/fix/settings-nav-glass. 
  _fix(admin): readable settings bar on phones in the glass theme_

* Fix(admin): readable settings category bar on phones in the glass theme. 
  _On phones the settings categories stick under the top bar while the page
scrolls beneath them. In the glass theme their background is the thin
card glass with no blur, so the settings' text showed through the chips.
Below 992 px the bar now uses the strong glass with a blur, like the
other bars of the theme; desktop and the default theme are unchanged._

* Merge pull request #162 from Hiddify-Official/feat/settings-option-icons. 
  _feat(admin): coloured icons for settings options_

* Feat(admin): coloured icons for settings options. 
  _Each select option in Settings now has an icon that says what the option
says, on a soft tile of its own colour: Low / Middle / High as one, two
and three level bars, No Wait a bolt, Standard a shield, WARP's Disable /
All / Only Blocked and Local a ban / globe / filter, uTLS the browser or
system, the proxy cores, Release / Beta, and the countries' flags (Russia
included). The WARP mode description uses the same icons as its options.
Options without an entry keep their label as before._

* Merge pull request #161 from Hiddify-Official/feat/no-emoji-all. 
  _feat(admin): icons and SVG flags in place of emoji_

* Merge branch 'dev' into feat/no-emoji-all. 

* Merge pull request #160 from Hiddify-Official/feat/dns-presets. 
  _feat(admin): DNS server picker with presets_

* Feat(admin): DNS server picker with presets, applied to the OS too. 
  _Settings > DNS Server is now a grouped dropdown: normal DNS (Cloudflare,
Google, Quad9, OpenDNS, Control D), ad blocking (AdGuard, Control D,
Comodo) and ad blocking + adult filter (AdGuard Family, Control D), each
with its two addresses, plus "Custom" for up to four IPv4/IPv6 addresses
(checked before saving). The old single "1.1.1.1" value shows as
Cloudflare.

dns_server may now hold several comma-separated IPs: hiddify-core uses
the first one and masterdns all of them before its defaults._

* Merge pull request #159 from Hiddify-Official/feat/ios-rounded-fields. 
  _feat(admin): iOS-style rounded corners on every field and dropdown_

* Feat(admin): iOS-style rounded corners on every form field and dropdown. 
  _Form fields had Aura's 6px corners. The theme preset now gives every form
field one soft radius (12px: text, number, password, search, date, Select,
MultiSelect, AutoComplete, Textarea, input groups, and the chip inputs that
follow --p-inputtext-border-radius), their dropdown panels 14px and the
options in them 8px. Rounded but not a pill; elements that were pills stay
so. Sizes and behaviour are unchanged._

* Merge pull request #158 from Hiddify-Official/fix/caddy-mobile-menu. 
  _fix(admin): the phone menu reads clearly on the light glass themes_

* Fix(admin): the phone menu reads clearly on the light glass themes. 
  _On a light glass (colour) theme the side menu is the light glass of the
cards. On phones it slides in over the page and its dark mask, which showed
through and made the menu grey and murky. Below the desktop layout the
light theme now takes a glass between the light and the dense one (about
70%) with a stronger blur: the page still glows through, the text reads
clearly. The dark theme and desktops are unchanged._

* Merge pull request #157 from Hiddify-Official/feat/mobile-menu-tab. 
  _feat(admin): a tab on the screen's edge opens the menu on phones_

* Feat(admin): a tab on the screen's edge opens and closes the menu on phones. 
  _On phones and tablets the side menu opened only from the top bar's ☰. A
small tab now sits at the middle of the screen's start edge: a tap slides
the menu in (the sidebar's own transition), the tab rides along at its edge
with its arrow turned back, and a second tap slides it out. RTL follows the
start edge; desktops do not show it. Solid on the glass themes._

* Merge pull request #156 from Hiddify-Official/fix/domain-switch-rtl. 
  _fix(domains): the edit dialog's switches stay inside their cards_

* Fix(domains): the edit dialog's switches stay inside their cards. 
  _In the domain dialog's Advanced, the "Resolve IP" and ECH switches sat in a
flex row with their text and shrank when the text was long (Persian, two
cards side by side). PrimeVue slides the handle by the switch's set width,
so a squeezed switch put its handle outside the track and the card. The
switch keeps its width now and the text wraps._

* Feat(admin): Lion and Sun flag for Iran. 
  _Iran's flag in the panel (country setting, the Persian language, nodes
in Iran) is the Lion and Sun flag: the public-domain state flag of
1964–1980 from Wikimedia Commons, cropped to 4:3 around the emblem like
the other flags._

* Feat(admin): icons and SVG flags in place of emoji. 
  _Emoji still reached the admin panel through text from the server (setting
descriptions, option names, labels with a mid-text warning, notices,
template-variable help, generated proxy names, domain aliases) and from
the UI itself (language and node flags, the Telegram demo, the broadcast
preview buttons, the drag-handle glyph in the domains help).

- emoji-icons.ts maps every emoji used in the translations to a PrimeIcon
  of the same meaning (warnings orange, bans red, coloured dots keep
  their colour); IconText renders plain text with them, iconizeHtml does
  the same for sanitized HTML. The strings keep their emoji for the
  legacy pages and the Telegram bot.
- Flags are SVG images from flag-icons (one small file each, never
  inlined), so they look the same on Windows, which has no flag emoji.
- Select options keep an emoji-free text for screen readers and typing;
  toasts and server error messages drop the emoji, since they show their
  own severity icon._

* Feat(admin_v2): grouped, searchable "Show configs of" picker on the Domains page. 
  _- New ShowDomainsPicker: an "All domains" switch, then one section per server
  (this server first, then nodes), each grouped as Fake TLS & Reality, CDN, then
  real certificate; search, quick filters with counts, tick a server or group at
  once; rows show each domain's alias and download domain.
- domains-page API: show_options now include each domain's download domain.
- "Show configs of" is offered on sub-link domains, or on every domain while no
  sub-link domain exists (no longer limited to real-certificate domains)._

* Merge branch 'dev' of github.com:hiddify/hiddifypanel into dev. 

* Merge pull request #155 from Hiddify-Official/fix/show-domains-cdn. 
  _fix(domains): a new domain is offered in "Show configs of" at once_

* Fix(domains): a domain just added is offered in "Show configs of" at once. 
  _The edit dialog's "Show configs of" list came only with the options call,
which takes seconds (it works out the proxies that fit each kind of
domain: about 5 s on the test server) and was asked again after every
change. A domain just added (e.g. a CDN domain with valid TLS) was missing
from the list, or the list was empty, when the dialog was opened before
that answer.

The list is quick to build (10 ms), so it now comes with every domains
list (load, add, edit, delete, reorder) and the dialog uses it; the options
call still sends it for older pages._

* Merge pull request #154 from Hiddify-Official/feat/node-os-logo. 
  _feat(nodes): the node's OS as its card's logo, details on a click_

* Feat(nodes): each node's operating system, as its card's logo and on a tap. 
  _The card's icon was the same server glyph for every node. A node's panel now
reports its operating system in the dashboard's host info (/etc/os-release:
ID, NAME, VERSION_ID, PRETTY_NAME; kernel and architecture), and the new
nodes/<id>/os/ asks a node for it with the parent's key (kept an hour).

The card shows the OS as an app icon in the panel's soft style (Ubuntu,
Debian, CentOS, Rocky, Alma, Fedora, Alpine, Arch, openSUSE, Red Hat, Mint,
Gentoo, FreeBSD; Tux for any other Linux; the old glyph when not known): a
tile tinted with the brand colour, a gloss and a fine border, the logo in
the brand colour (a lighter one in the dark theme for black / navy brands).
With the mouse on it the logo turns and bounces and a band of light sweeps
the tile. A tap opens a small popover with the OS, its version, the kernel
and the architecture. Logos from Simple Icons (CC0)._

* Fix(server_ip): prevent auto-discovered IPs from being registered to the same machine. 
  _Added a check in the bulk_register method to skip registering auto-discovered IPs if they belong to the current machine. This ensures that only unique child IDs are processed, improving data integrity during bulk operations._

* Refactor(domains): simplify domain row structure and improve layout consistency. 
  _Updated the DomainsView component to streamline the rendering of domain rows. Removed the conditional class for chosen proxies and adjusted the layout logic to ensure all proxies and configurations are displayed consistently. This change enhances the visual alignment of domain rows, maintaining uniform height and improving overall readability._

* Merge pull request #152 from Hiddify-Official/fix/domain-row-height. 
  _fix(domains): every domain row the same height_

* Fix(domains): every domain row the same height. 
  _A row without a line of chosen proxies was shorter than one with it (65 vs
87 px), and the fake-TLS front domains were drawn smaller. Every row's head
is now at least as tall as a row with that line, with its lines kept
together in the middle, so nothing moves inside a row; the fronts keep
their quieter look at the same size. Phones are unchanged (the cards were
already the same height there)._

* Merge pull request #151 from Hiddify-Official/feat/domain-badge-cards. 
  _feat(domains): certificate details and TLS modes on hover cards_

* Feat(domains): a certificate's full details and the TLS modes on hover cards. 
  _Hovering a domain's certificate badge showed a few lines of text (a hint,
the issuer, the expiry), and a Reality / Fake badge only "Fake and Reality
TLS domains do not need a certificate of their own".

- The domains API reads the stored certificate (cached per PEM): when it
  was issued, the names it covers, its key and the issuing organisation;
  with the stored fingerprint and auto-renew.
- The certificate badge opens a card in the badge's colour: its state and
  hint, a bar of the life left with the issue and expiry dates (amber under
  three weeks, red under one), then issued by, covers, key, auto-renew,
  fingerprint, and the last error when it failed.
- A TLS mode badge (Reality, Fake, DNS, a built-in server's fake-TLS name)
  opens a card that says what the mode does, that it needs no certificate
  and which name (SNI) it shows. Solid on the glass themes._

* Merge pull request #147 from Hiddify-Official/feat/dashboard-tile-tips. 
  _feat(dashboard): readable hover cards for tiles and charts_

* Fix(dashboard): the usual pointer over the top tiles. 
  _A tile with a hover card set cursor: help, so the pointer turned into a
question mark over the four tiles; it stays the usual pointer now._

* Fix(dashboard): a tile's sparkline tip next to the pointer. 
  _The tip (day and value) is position: fixed, but the tile lifts on hover with
a transform, which makes the tile its containing block: the tip landed as
far below as the tile is from the top of the page, often behind the cards
below. It is rendered in <body> now (Teleport), and under the pointer so
it does not cover the tile's big number._

* Feat(dashboard): the charts' hover card like the tiles'; solid on glass themes. 
  _- Every dashboard chart shows the page-text tooltip (it was the canvas one
  in left-to-right languages) as the tiles' card: the hovered point on top,
  a row per series (its colour, its name, the value in bold at the end),
  totals under a dashed line (_chart-tip.scss).
- A tile's sparkline tip: the day quiet, the value bold in the line's
  colour.
- The colour (glass) themes make the content background see-through, so
  the page's text showed through these cards; they get a solid surface
  there._

* Feat(dashboard): the KPI tiles' hover card, readable. 
  _Hovering a top tile showed its numbers as wrapped "label: value" lines of
white text on the dark tooltip. It is now a light card in the page's
colours: the tile's icon and name, then one row per number with the label
at the start and the value, bold, at the end. The tile's own number comes
first in the tile's colour; dark mode and RTL follow the theme._

* Merge pull request #148 from Hiddify-Official/fix/config-health-labels. 
  _fix(dashboard): card titles and Config Health app names in title case_

* Fix(dashboard): card titles in title case. 
  _The dashboard's cards read Usage Trend, Usage Comparison, Users Trend,
Users Comparison, Config Health and Node Health (the notice that points to
Config Health too). The Config Health card's apps read "Hiddify / Sing-Box"
and "XRay (v2rayN, v2rayNG, Happ, …)"._

* Merge pull request #138 from Hiddify-Official/fix/sidebar-keep-active. 
  _fix(admin): keep the open page's menu entry in view after a reload_

* Fix(admin): keep the open page's menu entry in view after a reload. 
  _A reload started the side menu scrolled to the top, so a page low in it
(Templates, Backup, …) was out of sight. The menu now scrolls its entry to
the middle on load and when the phone's menu opens; after a move from within
a page it only scrolls when the entry is out of view (no jump on a click in
the menu)._

* Merge pull request #137 from Hiddify-Official/fix/base-config-labels. 
  _fix(admin): proper names and colors for cores, sides, template categories_

* Feat(admin): names and colors for template categories. 
  _Server Inbound, Client Outbound and Base Config instead of the raw values,
each with a color of its own: a tag in the Category column, a dot in its
filter, and the name in the editor's select._

* Feat(admin): core colors in the templates' core filter. 
  _Like Base Configs and Proxies: each core's color before its name, sorted by
name._

* Feat(admin): core colors in the core filters. 
  _The Core filter of Base Configs and the Server core filter of Proxies show
each core's color before its name, like the Categories filter; the proxies'
Server core tags get that color too (they were all plain), and the filter
lists sort by name._

* Fix(admin): proper names for base config sides and cores. 
  _Side shows "Server" / "Client" and every core its name (Clash, DNS Proxy,
Firewall, HAProxy, Hiddify Core, IP Scanner, Rust-rpxy-L4, SingBox, SNI
Scanner, SubLink, Telemt, WireGuard, XRay) in the list, its filters (sorted
by name) and the editor, instead of the raw values._

* Merge pull request #135 from Hiddify-Official/feat/proxy-off-dim. 
  _feat(admin): fade switched-off proxies in the proxy list_

* Feat(admin): fade switched-off proxies in the proxy list. 
  _A proxy that is off (or kept off by a parent setting) gets a veil of its
row's colour over its cells, so on and off read at a glance; its switch and
buttons stay clear, and the row comes back on hover._

* Merge pull request #134 from Hiddify-Official/feat/smooth-reorder. 
  _feat(admin): live, smooth drag to reorder domains and users_

* Feat(admin): live, smooth drag to reorder domains and users. 
  _Domains (desktop and phone) and the users table now move like the phone
user cards: the dragged row follows the pointer, the rows it passes slide
aside, and on release it glides into place (Escape puts it back). One
shared composable, useDragSort, replaces the browser's own drag (which only
showed a drop line) and PrimeVue's row reorder; the order is saved as before._

* Merge pull request #133 from Hiddify-Official/feat/mobile-user-reorder. 
  _feat(admin): move users by a drag handle on phones too_

* Feat(admin): move users by a drag handle on phones too. 
  _The users page's cards get the table's drag handle: a finger (or mouse) on
it lifts the card, the cards it passes make room, and the page scrolls near
the screen edges. The drop is saved like a table row reorder (pinned users
stay above the others, a group stays within its admin); muted with a hint
while a sort orders the cards._

* Merge pull request #132 from Hiddify-Official/fix/ping-panel-opaque. 
  _fix(admin): solid ping panel in the colour themes_

* Fix(admin): solid ping panel in the colour themes. 
  _The Smart Caddy themes turn --p-content-background into see-through glass,
so the node card's text showed through the ping panel lying over it._

* Merge pull request #131 from Hiddify-Official/feat/login-animated-bg. 
  _feat(login): flowing colour waves behind the admin sign-in card_

* Feat(login): flowing colour waves behind the admin sign-in card. 
  _A WebGL canvas draws soft, never-repeating colour waves (domain-warped
simplex noise, light and dark palettes) at half resolution, paused while
the tab is hidden and still under reduced motion. The CSS blobs stay as
the fallback when WebGL is missing, and drift faster._

* Merge pull request #129 from DrvpnTM/fix/backup-server-ips. 
  _fix(backup): do not restore the old server's auto-detected IPs_

* Fix(backup): do not restore the old server's auto-detected IPs. 
  _A backup carries the server IPs found on the machine it was made on
(is_auto). Restored on another server they were added to its IP list,
so the new-domain dialog offered the old server's IPs for the DNS
record next to the real ones. Skip this server's auto-detected IPs when
restoring: the server finds its own again; IPs added by hand and other
nodes' IPs are restored as before._

* Merge pull request #126 from Hiddify-Official/feat/sync-log-readable. 
  _feat(nodes): recent syncs in words, with names, secrets hidden_

* Merge branch 'dev' into feat/sync-log-readable. 

* Merge pull request #125 from Hiddify-Official/fix/node-unreachable-error. 
  _fix(nodes): explain unreachable nodes, re-check, notify_

* Feat(nodes): an unreachable node in the notifications; other node errors explained. 
  _The top bar's notifications list each node this panel cannot reach, with the
reason and what to do (nodes/problems/, checked at most every 2 minutes); a
check on the Nodes page updates it at once. "Sync now", the dashboard's disk
details of a node and the Ping window say why in the panel's words too._

* Fix(nodes): Sync details explains why the node could not be asked. 
  _The dialog showed the raw HTTP error with the node's secret path. It now shows
the same explanation card as the Nodes page (what happened, why, what to do,
technical details to copy) with a Check again button._

* Fix(nodes): explain why a node is not reachable and how to fix it, check again. 
  _"Not reachable" and the live charts showed the raw HTTP error, with the node's
secret admin path. The panel now sorts the failure (key refused, timeout,
refused, DNS, TLS, CDN, not the panel, node error, no address) and the Nodes
page explains it in the panel's language: what happened, why, what to do, and
the technical text behind a copy button. A refresh button next to "Not
reachable" checks the node again._

* Merge pull request #124 from Hiddify-Official/feat/icon-hover. 
  _feat(admin): menu and Settings icons come alive on hover_

* Feat(admin): menu and Settings icons come alive on hover. 
  _A soft pop and sway when the mouse is over a side menu item or a Settings
category; only with a mouse, and not when reduced motion is asked for._

* Merge pull request #122 from Hiddify-Official/fix/idle-navigation. 
  _fix(admin): menu clicks do nothing after the panel was updated_

* Fix(admin): a menu click does nothing after the panel was updated. 
  _A tab left open across an update still asks for the old build's page files,
which are gone (404), and the router dropped the error: the click did nothing.
On such an error, load the page it was going to from the server (the new
build); once per address within 10 s, so a really missing file cannot loop._

* Merge pull request #120 from Hiddify-Official/feat/short-names. 
  _feat(admin): shorten long user names, full name on hover_

* Feat(nodes): long names shortened in Sync details' user and admin lists. 
  _The lists behind the Users and Admins tiles in Sync details cut a name after
20 letters (15 on a phone) with "…", the full name on hover, like the Users
page. The cut is in shared/utils/short-name.ts for both._

* Fix(admin): keep a long name inside the link dialog's title. 

* Feat(admin): shorten long user names (20 letters, 15 on phones), full name on hover. 

* Feat(nodes): recent syncs in words, with names, secrets hidden. 
  _Each recent sync in Sync details was a kind, a source tag, a number and
key=value pairs; opened, short ids and the raw JSON. Now it says what
happened ("5 users received from the main panel", "Traffic of 2 users sent
to the main panel") with its direction, and opened it lists the users,
admins, outbounds or domains by name with their state. The JSON stays behind
"Technical data", with secret values (keys, passwords, tokens) hidden._

* Merge branch 'dev' of github.com:hiddify/hiddifypanel into dev. 

* Merge pull request #116 from Hiddify-Official/fix/users-rtl-sort-mask. 
  _fix(users): blank Users page on phones in RTL_

* Fix(users): blank Users page on phones in RTL (sort strip mask on the whole page) 
  _":global([dir='rtl']) .u-sorts" compiles to a bare [dir='rtl'] {} in scoped CSS, so in RTL the
sort strip's fade mask was applied to the page itself; phone browsers then stopped painting the
page part way down. The fade is now a gradient drawn over the strip's end (html[dir='rtl'] for
its direction), with no mask-image._

* Merge pull request #117 from Hiddify-Official/fix/node-register-locale. 
  _fix(nodes): adding a node fails with "outside of request context"_

* Feat(nodes): Add node errors in the panel's language: where, what happened, what to do. 
  _The error box shows which side failed (icon and title), one sentence on what
happened and a "What to do" box, all translated; the registration id and a
"Copy technical details" button stay for support. The node's raw (English)
message is no longer shown, only copied. Texts are split into nodes.errors
(what) and nodes.errorFix (what to do) for every code, in English and Persian._

* Fix(nodes): "Working outside of request context" when adding a node. 
  _The node registers in a background job (no request), and the locale selector
read request.base_url: the first translated text in the job raised, so a
registration that failed for a real reason came back as a bare HTTP 500.
get_locale now falls back to the request's choice or the admin language
outside a request.

The parent shows a 5xx from the node as its own error (node_error: an internal
error on the node, see its log under the registration id) with the node's
message, instead of "the node refused" and the raw JSON body._

* Merge pull request #118 from Hiddify-Official/feat/users-note-filter. 
  _feat(users): "Note" in Filter by tag_

* Feat(users): "Note" in Filter by tag. 
  _Filter by tag gets a "Note" entry after "Pin" (notebook icon, with its count): it lists the
users an admin wrote a note for, alone or together with tags, like "Pin"._

* Merge pull request #119 from Hiddify-Official/feat/note-preview. 
  _feat(users): short note beside the name, a note mark next to Telegram_

* Feat(users): a note's first three words beside the name, a note mark next to Telegram. 
  _The note beside a user's name shows its first three words and "…" when there is more;
hovering, focusing or tapping them opens the whole note on the ruled notebook sheet, kept
open while the pointer is on it. Users with a note also get a notebook mark in the row's
extras, next to Telegram (table and phone cards): only a mark, nothing on hover. The sheet
is its own component (NoteSheet), shared with the Admins page's notebook button._

* Feat(admin): notes on a notebook sheet next to Edit on the Admins page. 
  _A notebook button before Edit, only on admins with a note, opens the note on a small
pale-yellow ruled sheet (NoteButton). The Admins page loses its Note column._

* Fix(render): render the gettext helper without flask-babel. 
  _dump-client-configs and some CLI paths have an app context without flask-babel
registered: the translation helper fell back to the message id and failed on a
missing locale, which broke xray and sublink rendering there._

* Feat(domain): warn when a REALITY domain does not support X25519. 
  _REALITY authenticates through the client's X25519 key share. A site that only
accepts NIST curves (x1.com) answers with a HelloRetryRequest, the server then
relays the real site and every client fails. A REALITY domain is now checked
with a TLS 1.3 ClientHello offering only X25519; saving one that fails shows a
warning, and the domain wizard and picker treat it as not REALITY friendly._

* Fix(client): config fixes found testing every config in hiddify-core and Xray. 
  _- VLESS (hiddify-core / sing-box): Vision flow only on TCP+REALITY, as in the
  sublink and Xray templates; it was set on WS/gRPC/XHTTP too and broke them.
- A subscription has the panel's own proxies only: another child's proxies (its
  node configs too) were rendered on this panel's domains, not served, and came
  out twice ("tag §1").
- VLESS without encryption and Trojan over plain HTTP are never offered.
- gRPC over plain HTTP (h2c) presets start disabled: CDNs do not pass it.
- hiddify-core: raw TCP (VLESS / VMess / Trojan without a transport) and raw
  HTTP over TLS / REALITY ("version": 1 of the http transport, Hiddify 5.1+).
- SS FakeTLS client: no "tls" field (the simple-obfs plugin makes the TLS look).
- Xray: Hysteria 2 and plain Shadowsocks 2022 outbounds; WebSocket "host"
  instead of the deprecated Host header; an HTTP/1.1 xhttp leg uses the
  "android" uTLS hello, since Xray's chrome hello offers h2 whatever "alpn"
  says and a CDN then answered in HTTP/2._

* Fix(server): raw Trojan over REALITY, SS FakeTLS in hiddify-core, rpxy-l4 untyped streams. 
  _- REALITY termination: what is not VLESS goes, per ALPN, to a Trojan inbound of
  its own domain, which serves raw Trojan over REALITY and passes the rest on to
  the gateway as before (Trojan clients offer h2 too, so ALPN alone could not
  tell them apart).
- SS FakeTLS is a hiddify-core inbound with its simple-obfs server (obfs_mode
  tls) instead of the obfs-server service; a stranger is passed to the TLS decoy
  of :443 through the decoy-tls front (no PROXY header needed).
- rpxy-l4 takes a stream for TLS only when every record it read is a handshake
  record, so a simple-obfs ClientHello followed by data in the same read was
  sent to the default route. Its untyped streams now go to HAProxy, which finds
  the SNI proxies again.
- Xray's raw HTTP Trojan inbound takes no PROXY protocol: behind it Xray's first
  read is cut at 256 bytes and the Trojan inbound rejected a short request (400).
- hiddify-core 5.1 (sing-box 1.14+): remote rule-sets get an HTTP client of
  their own, else the core refuses to start._

* Fix(proxy): improve handling of HTTP and HTTPS traffic in HAProxy configurations. 
  _- Updated comments for clarity on HAProxy's handling of cleartext and TLS traffic.
- Adjusted backend routing to ensure proper handling of plain HTTP after TLS termination.
- Enhanced frontend configurations to differentiate between cleartext and post-TLS traffic.
- Ensured that redirects to HTTPS are correctly applied based on client connection type._

* Fix(proxy): keep node-configs when HTTP proxies are off; fix legacy child ping. 

* Fix(proxy): keep User Configs when HTTP proxies are off (#5622) 

* Fix(proxy): omit VLESS Vision flow on non-REALITY links (#5640) 
  _Only emit xtls-rprx-vision for TCP+REALITY (terminator); WS/gRPC/XHTTP
subscription and client configs no longer get a bogus flow._

* Feat(domains): per-domain FinalMask tricks with TLS Fragment + custom JSON. 
  _Move tricks into Advanced, hide panel tls_fragment settings, and emit
FinalMask {tcp:[{type:fragment,...}]} for clients instead of dialerProxy._

* Feat(users): bulk-create users from Add menu and export their links. 
  _Add a split-button action to generate many users with a shared package
and name prefix, then show copy/downloadable subscription links (#4918)._

* Feat(admins): add grantable capabilities  for sub-admins. 
  _Let parents control what agents can do (preferred outbound, sublinks,
domains, outbounds, …) and block granting capabilities they lack (#5645)._

* Feat(security): enhance session security and enforce HTTPS redirects. 

* Merge branch 'dev' of github.com:hiddify/hiddifypanel into dev. 

* Merge pull request #105 from Hiddify-Official/feat/donation-icons. 
  _feat(donation): icons instead of emoji, other help behind Show More_

* Feat(donation): icons instead of emoji, no intro text, other help behind Show More. 
  _The dialog builds its own text from admin_v2 keys instead of the server's
Donation.description HTML: a Payment Methods heading, the wallets, then
"We need also other help" (closed by default) with an icon per item and
the contact address._

* Merge pull request #108 from Hiddify-Official/feat/users-mobile-sort. 
  _feat(users): sort buttons for the phone cards_

* Feat(users): sort the phone cards like the table's columns. 
  _Small buttons next to Select all, one per sortable column (ID, status,
name, usage, expiry, last connection): a tap sorts ascending, the next
descending, the third goes back to the admin's own order._

* Merge pull request #111 from Hiddify-Official/feat/apply-log-telegram. 
  _feat(apply): send a log to my Telegram from the Actions page_

* Feat(apply): send a log to my Telegram from the Actions page. 
  _A Telegram button next to View and Download sends the whole log (as the
download gives it) to the admin's Telegram through the panel's bot. It shows
only when the panel has a bot, and stays disabled until the admin has
connected Telegram (My account)._

* Merge pull request #109 from Hiddify-Official/fix/account-topbar-active. 
  _fix(admin): My Account stays visible in the top bar when open_

* Fix(admin): My Account stays visible in the top bar while its page is open. 
  _The active style used the primary color, which is the default themes' top
bar color, so the icon faded into it. It now uses the bar's own text color,
as the notifications and appearance buttons do; the glass theme keeps its own._

* Merge pull request #104 from Hiddify-Official/fix/title-case-names. 
  _fix(admin): menu and page names in title case_

* Fix(admin): Send Message in the sidebar (server menu translations) 
  _The sidebar item comes from the server's compiled catalog, not from the
admin UI's JSON: the English .po and .mo get the same text as en.json._

* Fix(admin): Send Message, Config Tester, Text Decoders, SSH Terminal in title case. 
  _The Tools and Manager menu items, their page titles and the Settings
"Show Advanced Settings" switch; the Text Decoders page was titled "Utils"._

* Merge pull request #103 from Hiddify-Official/fix/domain-mode-names. 
  _fix(admin): Domain modes column as Direct, Relay, CDN_

* Fix(admin): domain modes column in their own spelling (Direct, Relay, CDN) 
  _The collapsed summary showed the raw keys; it now uses the same labels as the
expanded tags and the Domain modes filter._

* Merge pull request #102 from Hiddify-Official/fix/category-colors. 
  _feat(admin): proxy categories in their own colours_

* Feat(admin): proxy category colors. 

* Fix(admin): protocol, category, core and mode names in their own spelling. 
  _Protocols were shown in capitals (VLESS, HYSTERIA2, WIREGUARD…) or in
whatever case a text happened to use, and proxy categories as their raw
tags (down:tls_h1, node_configs). They now have one spelling:
- Protocols: VLess, Trojan, VMess, Shadowsocks, Socks, V2Ray, SSR, SSH,
  TUIC, Hysteria, Hysteria 2, WireGuard, Naive, Mieru, AnyTLS, DNSTT,
  Slipstream, MasterDNS, Snell, Telegram.
- Cores: DNS Proxy, HAProxy, Hiddify Core, rust-rpxy-L4, Telegram, XRay
  (Proxies, Base Configs and Templates: columns, filters, editors).
- Modes: Domain L7 Gateway, Domain SNI Gateway, Domain DNS Gateway,
  Multi-Domain Auto Ports, Multi-Domain Static Port, IP-Based, No Inbound
  (English; the quick filter uses the same names as the column).
- Built-in categories by name (Down:TLS_H1, Node Configs, gRPC,
  HTTPUpgrade…); a category an admin typed is shown as written, and the
  stored values do not change.
shared/utils/protocols.ts holds the name maps (and a share link's scheme:
ss, hy2, wg… → its protocol); the Proxies list (column, categories,
filters), the proxy editor and the config tester's viewer use them. The
texts (admin UI and setting labels, all languages) use the same spelling;
link schemes (vless://) and JSON samples stay as they are. The Proxies
page is titled "Proxies", as in the menu._

* Merge pull request #100 from Hiddify-Official/feat/no-emoji. 
  _feat(admin): icons in place of emoji_

* Feat(admin): icons in place of emoji. 
  _The page's own emoji are icons now, chosen for what they stand for:
- Domains row extras: ECH (envelope), resolve IP (search), forced IPs (map
  marker), fronting (ID card), download domain (download), as in the
  domain dialog.
- Custom proxies: split upload / download TLS layers get the upload and
  download icons.
- User form: "unlimited" is an infinity icon (inline SVG; PrimeIcons has none).
- SSH files: no rights at all is a lock icon.
- Language and country pickers: the panel default, an unknown language
  and "other country" get a globe icon (real flags stay).

Kept on purpose: flags, the drawings of Telegram messages (what the bot
really sends), the type emoji that go into config names, and names that
are data (built-in proxy names)._

* Merge pull request #99 from Hiddify-Official/feat/domains-guide. 
  _feat(domains): a one-time spotlight on reordering domains_

* Feat(domains): a one-time spotlight on how to reorder domains. 
  _The first time the Domains page shows two domains or more, a spotlight
loops a small list drawn like the real rows: a finger takes row 3 by its
handle and drags it to the top, the others move down, the numbers stay.
Three steps are lit with it (grab the handle, drag and drop, the order is
saved and configs follow it); "Got it" and it does not come back in this
browser. It follows the page's direction (mirrored in Persian)._

* Feat(domains): icons in place of emoji in the domain dialog. 
  _The TLS modes (Valid, Fake, Reality, DNS, Telegram, ShadowTLS, SS FakeTLS)
have the icons of their badges on the Domains page, in their colours (Fake
orange as there). The Advanced fields have icons too, and their labels
lose the emoji they started with (fronting, download domain, forced IPs,
resolve IP, ECH) in all languages._

* Feat(domains): a roomier, mirrored domain row: type icons, copy, touch drag. 
  _The row used a narrow column for everything, so on wide screens most of
the card was empty while its details were squeezed together:
- The head holds the order, the type's icon, the address with a copy
  button before it, the alias and the TLS badges, with the certificate
  button and the actions at the far side.
- The details (custom proxies, "show configs of", ports, server and
  download domain, fronting) are tiles across the card's whole width,
  one column on a phone.
- The types have their own icons (server, cloud, relay, bolt, link) in
  place of emoji, also in the type picker, the wizard and the dialog (the
  emoji stays for the suggested config names).

The row was kept left-to-right in right-to-left languages, so in Persian
only the text moved: the whole row now follows the page's direction (the
domain name itself stays left-to-right).

The Move up / Move down buttons are gone. The handle drags with a mouse,
and now with a finger or pen too (pointer events: the browser's own drag
needs a mouse), and takes the keyboard (focus it, ↑ / ↓)._

* Merge pull request #110 from Hiddify-Official/fix/apply-title-case. 
  _fix(admin): Actions page names in title case_

* Fix(admin): Apply & Status, Apply Changes, Restart Services, Check Status. 

* Fix(i18n): close the notifications block in five translation files. 
  _Merging dev into feat/notifications lost the "}," that ends the adminV2
notifications block in fr, my, pt, ru and zh: those files were not valid
JSON. The brace is back; nothing else changes._

* Merge pull request #112 from Hiddify-Official/feat/apply-tools-colors. 
  _feat(admin): Actions tools bigger, each in its own color_

* Feat(admin): Actions tools bigger, each in its own color. 
  _Reset Cache (teal), Public ports (pink) and Live connection test (gold), at
normal size; none of them uses an action card's color._

* Merge pull request #113 from Hiddify-Official/feat/theme-icon-sliders. 
  _feat(admin): sliders icon for the top bar's appearance menu_

* Feat(admin): sliders icon for the top bar's appearance menu. 

* Merge pull request #93 from Hiddify-Official/feat/domain-notices. 
  _feat(domains): certificate problems in the notifications_

* Feat(domains): certificate problems and save warnings in the notifications. 
  _Domains whose certificate does not work (getting it failed, its renewal
failed, rate limited, expired, self-signed, missing) show in the topbar
notifications on every page, errors first, from a light
domains-page/problems/ endpoint. The warnings a save answers with (a toast
on the page) also stay there for three days or until dismissed._

* Merge pull request #92 from Hiddify-Official/fix/sub-domain-order. 
  _fix(sub): configs follow the Domains page order_

* Fix(sub): configs follow the Domains page order. 
  _Two things broke the order. Domain.ordering() sorted every panel's domains
together by sort_order, and each Domains page numbers its rows from 0: a
parent's domains interleaved with its nodes'. And the no-inbound proxies
(the nodes' configs, user configs, Telegram web) sat at the first domain,
so hundreds of node configs came between the first domain and the second.
Each panel's domains now stay together, this panel first, and no-inbound
proxies come after the domains' configs._

* Merge pull request #91 from Hiddify-Official/feat/domain-tls-colors. 
  _feat(domains): Reality, Fake and Valid TLS in their own colours_

* Feat(domains): Reality, Fake and Valid TLS in their own colours. 
  _The TLS mode was part of the green domain-type badge ("Direct · Reality")
next to a generic "Decoy TLS" badge. The mode now has its own badge in
place of that one: Reality violet, Fake orange, DNS slate, built-in
fake-TLS servers sky; Valid stays the green certificate badge._

* Merge pull request #90 from Hiddify-Official/fix/domain-add-ip. 
  _fix(domains): Add domain accepts IPv4 and IPv6 addresses_

* Fix(domains): Add domain accepts IPv4 and IPv6 addresses. 
  _The wizard only took names ("That does not look like a domain"), and its
port stripping cut the end off an IPv6 address ("::1"). The API's regex
took IPv6 only when written out in full. Addresses are now checked as
addresses and kept in their standard form (brackets removed, IPv6
shortened)._

* Merge pull request #89 from Hiddify-Official/feat/bot-check-status. 
  _feat(telegram-bot): "Check status" with address and services_

* Feat(telegram-bot): "Check status" shows the server's address and services. 
  _A "🩺 Check status" button in the admin bot's menu (not for agents) answers
with the server's public IP, its country (with the flag), city and
organisation, and the state of the Hiddify services: ✅ active,
⚠️ activating, ❌ failed or not running. Monospaced so the columns line up;
the address lookup is cached for an hour._

* Merge pull request #88 from Hiddify-Official/feat/backup-telegram. 
  _feat(backup): "Save on the Telegram" sends a backup to Telegram_

* Feat(backup): "Save on the Telegram" sends a backup to the admin's Telegram. 
  _With the admin's Telegram linked to the panel's bot, the Backup & restore
page has a "Save on the Telegram" button next to "Save on the server".
The backup is built in memory and sent by the bot with the automatic
backups' caption; no file is kept on the server._

* Merge pull request #87 from Hiddify-Official/fix/config-health. 
  _fix(config-health): test via the domain, explain errors, notify_

* Fix(config-health): test via the panel's domain; explain errors, also in the bell. 
  _The check fetched the subscription from the first domain, which can be the
server's bare IP: its certificate names the server's hostname, so the fetch
failed with an SSL hostname mismatch although nothing was wrong. A domain
name is now preferred; with only an IP the server asks itself without the
certificate check.

Errors get a kind (certificate, timeout, dns, unreachable, http, empty,
core) and the dashboard card explains each one and where to look, with the
technical message (subscription path removed) on demand and wrapped inside
the card. Failed configs get a reason in words. Config health problems also
show in the topbar notifications, errors first._

* Merge pull request #86 from Hiddify-Official/feat/notifications. 
  _feat(admin): panel notices in a top-bar notifications bell_

* Merge branch 'dev' into feat/notifications. 

* Merge pull request #85 from Hiddify-Official/feat/pwa-guide. 
  _feat(admin): animated install guide and Telegram spotlight_

* Feat(admin): Telegram prompt as an animated spotlight. 
  _The dashboard's Telegram prompt shows the bot in a looping chat: its
menu, the users with their usage, a user created from the chat, with
the three steps lit in sync. The install guide waits for the next
visit while the prompt is due, so only one spotlight shows at a time._

* Feat(admin_v2): animated "install as an app" guide on the dashboard. 
  _The install dialog listed two static steps and appeared once per visit on
any page, only when the browser offered an install. Now:

- A looping animation of the browser's own controls shows how to install:
  Safari on iPhone / iPad, Chrome on Android, Chrome on Windows, macOS or
  Linux (PwaInstallGuide.vue). The detected platform comes first; the
  others are one tap away, and the step being shown is lit in the list.
- It opens on the dashboard only (a node: its home), each time the panel
  is opened (once per page load), never when the panel already runs as
  the installed app.
- "Got it" closes it; with "Do not show this again" ticked it stays
  closed. Where the browser can install right away, "Install now" too.
- Strings in all 7 languages (fr, my, pt, ru, zh had none for it).

The user panel gets the same guide (hiddify-user-front)._

* Merge pull request #84 from Hiddify-Official/feat/menu-icons. 
  _feat(admin_v2): coloured menu icons and page title icons_

* Feat(admin_v2): coloured menu icons, and the page's icon before its title. 
  _- Each menu icon gets a vivid colour by what it is (menu-icons.ts), on a
  soft chip of that colour: Donation a red heart, Bug/Feature yellow,
  Users violet, Backup green, … Icons without a colour stay as before.
- PageHeader shows the icon of the page's menu item (found from the
  route, deepest match) before the title, in the same colour; an `icon`
  prop overrides it. All 21 pages that use PageHeader get it._

* Merge pull request #95 from Hiddify-Official/feat/node-ping. 
  _feat(nodes): a Ping panel on each node's card_

* Feat(nodes): a Ping panel on the node's card that pings until it is closed. 
  _A "Ping" button on each node card opens a panel over that card, under its
name: this panel pings the node's server once a second (ICMP, or the time
of a TCP connect to its panel port when ICMP is not possible) until the
panel is closed, with the latest time, min / avg / max / loss, a bar per
answer and the last lines. Each card has its own, so several nodes can be
pinged at once._

* Feat(nodes): "Show more" with the node's live network, CPU and RAM charts. 
  _Each node card has a "Show more" toggle under its buttons that opens the
node's live charts: network up/down, CPU and RAM, drawn like the
dashboard's Node health but for that node only. One feed (the dashboard's
system snapshot, which lists every node) runs every 5 s while a card is
open and keeps 60 samples: the last 5 minutes._

* Merge pull request #96 from Hiddify-Official/feat/node-flags. 
  _feat(nodes): the node's country flag before its name_

* Feat(nodes): the node's country flag before its name. 
  _The Nodes API gives each node's country (ISO code), from its address and
the panel's own MaxMind data (a name is resolved first), kept a day. The
card shows the flag before the node's name, the country's name on hover._

* Feat(admin_v2): panel notices in a topbar bell instead of page banners. 
  _The panel's notices (default domain, SSH password login, …) were banners
above every page.

- A bell in the topbar, next to the account icon, lists them; it is
  shown only while there are notices.
- A blinking red dot while some have not been seen; opening the list
  marks them seen (kept per browser, like dismissals). A notice whose
  text changes counts as new again. New ones are tagged until it closes.
- Each notice can be dismissed from the list, as from the banner; with
  none left the bell goes away.
- The banner component is removed; toasts for toast notices still show.
- Strings in all 7 languages._

* Feat(ip-lookup): add IP lookup functionality and integrate with API. 

* Feat(admin): implement user page customization for admins. 
  _- Introduced `admin_overrides.py` to manage settings that admins can customize for their users, including branding title, support link, language, and custom user page URL.
- Updated the API to allow admins to save their override settings.
- Added a new `UserPageForm` component for admins to edit their users' page settings.
- Enhanced the `MyAccountView` to display and manage user page customizations.
- Updated translations for user page customization features.
- Added unit tests for the new functionality in `test_admin_overrides.py`._

* Feat(proxy): add tcp_protocol_detection_timeout_msec configuration option. 

* Fix(proxy): handle service port conflicts for SNI proxies. 

* Feat(rawhttp): implement safe headers for rawhttp requests and enhance jinja rendering. 
  _- Added a new module `rawhttp.py` to handle browser-like headers for rawhttp requests, ensuring safe transmission behind HAProxy.
- Introduced `safe_headers` function to filter headers based on safety criteria.
- Updated jinja rendering functions to include `rawhttp_headers` for generating headers in templates.
- Enhanced `_jinja_choose_random` function to handle lists and strings more effectively.
- Added unit tests for the new functionality in `test_rawhttp_headers.py` to ensure correctness._

* Fix(hiddify-core): rawhttp header short for the Hiddify app too; choose_random takes a list. 
  _The Hiddify app's rawhttp (sing-box http transport) to an xray rawhttp inbound had the same long header: 5/10 with it, 9/10 short. choose_random split str(list) on commas, so sec-ch-ua-platform was "'Windows']" (or "['Android'") in every ws / httpupgrade / xhttp profile of the Hiddify app._

* Fix(xray): rawhttp configs failed every other connection (or 9 in 10 for VMess) 
  _The fake HTTP request header of rawhttp (xray tcp header type http) carried 15 browser-like headers (~650 bytes). Xray's server reads that header in one go and rejects one that arrives in two pieces ("failed to read request header > malformed MIME header: missing colon: \"Refer\""); a long header often did. Tested from the server: rawhttp vless direct 10/20 and vmess 2/20 before, 20/20 both with the short header (User-Agent, Accept, Connection, plus Host)._

* Merge pull request #79 from Plus98ir/feat/custom-user-page. 
  _Custom user page: any URL (e.g. a hiddify-user-front gh-pages build) as the user page_

* Merge branch 'dev' into feat/custom-user-page. 

* Merge pull request #83 from Hiddify-Official/feat/users-layout. 
  _feat(users): pin and reorder users, wider Usage, animated guide_

* Merge branch 'dev' into feat/users-layout. 

* Refactor: remove deprecated fake-TLS domain handling and update related logic. 
  _- Removed the FAKE_PROXY_MODES as they no longer mirror any domains.
- Updated ProxyPicker and TlsPicker components to reflect changes in proxy selection logic.
- Adjusted domain rules and configurations to ensure SNI proxies are handled correctly without fake domains.
- Updated translations to clarify proxy selection rules.
- Added tests to verify that Telegram MTProxy domains route correctly to telemt's listener._

* Make faketls ss proxy like other sni proxies. 

* Feat(users): pin from the tag circle, Pin in the tag filter, animated guide. 
  _- The pin button beside Edit (and on the phone cards) is gone: the tag
  circle's menu has "Pin" first (no edit button), and a pinned user's
  circle shows the pin before its tags.
- Filter by tag has "Pin" first, with the number of pinned users; it
  combines with tags like any tag (PIN_TAG = -1).
- The users guide shows each feature as a small looping animation of the
  real controls: pin from the tag menu, drag a row up, widen Usage from
  the Name edge (a still frame with reduced motion)._

* Fix(users): reorder within an admin's group; no text selection when resizing. 
  _- Grouped by admin, rows can be dragged again, but only among the users
  of the same admin; a drop into another admin's group is refused with a
  hint. Pinned users still stay on top within each group.
- Resizing the Name/Usage edge selected text across the rows in real
  browsers: the selection starts on the resizer's mousedown, before the
  "resizing" style applies. The mousedown is now prevented (PrimeVue
  still handles it)._

* Fix(users): pinned users stay on top in a column sort; no selection while resizing. 
  _- A column sort (name, usage, expiry, …) sorts the pinned users among
  themselves on top, then the others the same way; the table is lazy then
  and gets its rows sorted (PrimeVue's comparison), the header arrow
  still shows the sort. Grouping by admin sorts as before. The header
  checkbox still picks every user of the filter, not only the page.
- Dragging the Name/Usage edge no longer selects text across the rows
  (user-select off while resizing, any selection cleared at the end)._

* Fix(users): the usage bar follows the Usage column's width. 
  _The usage cell had a fixed width (11rem), so widening the Usage column
left the bar short. The cell now fills the column (at least 8rem), and
the bar fills the cell, wider or narrower._

* Feat(users): pin and reorder users, widen Usage, first-visit guide. 
  _- Pin: a button next to Edit (and on the phone cards) moves a user to the
  top rows; pinned users are tinted, with a line under the last one.
- Reorder: drag a row by its handle; pinned users reorder among
  themselves and the others stay below them (a drag across the two is
  refused with a hint). Works in a filtered or paged view: hidden users
  keep their places. Off while a column sort or grouping orders the rows.
- The order is per admin, on the server: admin_user.users_layout (JSON:
  pinned, order, guide_seen), GET/PUT admins/me/users-layout/, migration
  _v181. It is not part of the admin's synced data.
- Usage column: widened by dragging the Name column's edge (the only
  resize handle); the width is kept per browser.
- A first-visit guide, "Welcome to the new Users experience", shows
  pinning, reordering and the resize; "Got it" closes it for good.
- Strings in all 7 languages._

* Merge PR #80: align ShadowTLS, TUIC and Mihomo templates. 

* Fix(proxy): align ShadowTLS, TUIC and Mihomo templates. 
  _Align ShadowTLS routing and SS2022 keys, export AnyTLS for Mihomo,
preserve Vision flow on encrypted VLESS transports, and negotiate h3
on both sides of TUIC. Disable HTTPUpgrade fast-open and keep hidden
transport helpers out of standalone config tests._

* Merge branch 'dev' of github.com:hiddify/hiddifypanel into dev. 

* Merge pull request #81 from Hiddify-Official/feat/appearance-themes. 
  _feat(admin_v2): appearance menu: language, light/dark and glass themes_

* Fix(admin_v2): light color themes: visible dividers and readable main buttons. 
  _- Light glass set the content border color to white, so table row lines
  (users, admins), section dividers and outlines vanished on the frosted
  white. They get a faint dark line again; the glass cards keep their
  white edge.
- The main button's gradient in light starts from the color's 600 step
  (was a pale 300-ish shade under white text): 600 to 800, white text,
  readable for every color.
- The popup-only border workaround is no longer needed.

Dark mode is unchanged._

* Feat(admin_v2): three dark theme colors: graphite, space gray, dark brown. 
  _- New Smart Caddy colors, each a full palette with its gradient and glow,
  in light and dark: graphite (pencil lead), Apple's space gray, and a
  dark espresso brown.
- Ten swatches now: two rows of five.
- Their names in all 7 languages._

* Feat(admin_v2): every color in both themes, very bright text in dark. 
  _Two themes, light and dark, and each shows every color:

- Light + a color: frosted white glass over the color's glow; dark + a
  color: the Smart Caddy dark glass. The light/dark buttons work with any
  color again (no forced dark, no lock note).
- Dark text is very bright: white for text, 80% white for muted text,
  in every dark mode.
- Light glass: popups and dialogs keep a faint dark border, so the
  choices inside them stay outlined on the frosted white._

* Feat(admin_v2): glass theme swatches, flag-only language button, translucent white text. 
  _- The theme swatches are glass tiles: the color slightly translucent, a
  bright edge and a light sweep across the top.
- The language button shows only the chosen language's flag; its name is
  in the list, the tooltip and the aria label.
- Every dark mode (the Hiddify theme's and the Smart Caddy colors) writes
  text in translucent white: 92% for text, 64% for muted text, instead of
  grey (variables/_dark.scss)._

* Fix(admin_v2): Smart Caddy themes as in the original, white text, visible menu icon. 
  _- A color theme is PR #64's Smart Caddy look again: always dark (the
  light glass variant is gone). Light/dark is the Hiddify theme's
  choice; with a color theme the two buttons are disabled with a note.
- Dark glass sets white text (and 72% white for muted text), so labels,
  the menu and tables read on the translucent cards.
- The palette button stays visible while its menu is open: the active
  style uses the topbar's own text color instead of the primary color,
  which vanished on the primary-colored bar._

* Feat(admin_v2): one appearance menu: language, light/dark and Smart Caddy themes. 
  _Builds on the Smart Caddy theme: its colors become the themes of one
appearance menu in the topbar, next to the admin's language and light or
dark mode, instead of a second palette button.

- The language is one control: the flag and name of the language in use;
  a click lists the others (saved to the admin's account, the page
  reloads in it).
- Light or dark stays a choice of its own. Smart Caddy is no longer
  always dark: a light variant (frosted white glass over the color's
  glow) joins the dark one, so a color switches the whole page to the
  glass theme in either mode. "Hiddify theme (default)" switches back.
- _theme-caddy.scss: the color palettes apply in both modes, the glass
  rules are shared, and dark and light set their own surfaces; map keys
  quoted and sass:list used, so it compiles without warnings.
- The theme strings in all 7 languages._

* Feat(admin_v2): optional Smart Caddy theme in seven colors. 
  _A palette button in the topbar opens seven swatches (red, pink, orange, yellow, green, blue, purple). Picking one switches to the Smart Caddy look in that color: dark glass cards over a colored glow and gradient buttons. "Hiddify theme (default)" switches back. The panel's own look stays the default, and the choice is kept per browser._

* Merge pull request #82 from Hiddify-Official/feat/backup-caption. 
  _feat(backup): clearer Telegram backup message, no IPv6 link_

* Fix(backup): show only the link titles, not the IP or domain. 
  _The titles (Secure IPv4, Secure Domain, …) are the links; the address
after each one is no longer shown._

* Feat(backup): name each link's host, add panel and time, not-secure last. 
  _- Each line shows the domain or address it opens, so several domains
  no longer read as identical "Secure Domain" lines.
- A header names the panel (branding title, else HiddifyManager), its
  version and the backup time.
- The not-secure IPv4 link comes last: the secure ones are the ones to
  open, and the first kept under the 1024-character caption limit._

* Feat(backup): Telegram backup message: 🔒 for own links, no IPv6 link. 
  _- Secure links to the server's own IPv4 or domain (and relays) use 🔒;
  CDN links keep 🔐.
- IPv6 admin links are no longer sent: they do not open from most
  networks._

* Feat(acme): add deadline handling for certificate issuance and renewal. 

* Feat(clean-ip): introduce OperatorIpEditor component for managing IP and operator pairs. 
  _- Added a new OperatorIpEditor component to handle the input of IP addresses and their associated operators.
- Updated CleanIpView and DomainDialog to utilize the new OperatorIpEditor for better user experience.
- Refactored mergeCdnIp function to accommodate the new operator handling logic, including the use of "OTHER" for operators without specific addresses.
- Enhanced utility functions for parsing and serializing operator IPs.
- Updated translations for operator-related terms in both English and Persian._

* Custom user page: Settings > user_page_url (any static site or GitHub folder, e.g. a hiddify-user-front gh-pages build) served on the user's link, with the panel contract in window.__HIDDIFY__ 

* Merge pull request #76 from Plus98ir/feat/config-health. 
  _feat: config health — every config tested from the server every 6 hours, dashboard card, Telegram alert_

* Merge branch 'dev' into feat/config-health. 

* Merge pull request #77 from Plus98ir/feat/reality-sni-watch. 
  _feat(reality): REALITY SNI watch — find filtered SNIs from Iran and switch to a spare (by hand or automatically)_

* Feat(clean-ip): REALITY SNIs card — status per ISP, spares, switch, automatic switch, history. 

* Reality watch: switch only to a site REALITY really works with (a test connection through a throwaway xray server and client) 
  _TLS 1.3 + h2 (is_domain_reality_friendly) is not enough: www.microsoft.com passes it, but REALITY's handshake through it fails, so every client would break after the switch. Tested on the server: paltalk, speedtest, samsung work; microsoft does not._

* Reality watch: apply configs after a switch (rpxy-l4 routes port 443 by SNI and kept the old name) 

* Feat(reality): REALITY SNI watch — find filtered SNIs from Iran and switch them to a spare. 
  _The full clean IP test (run on a device in Iran) also opens a TLS connection to this server with each REALITY SNI and each spare SNI, the way a REALITY client does; SNI filtering cuts it, whatever the address. The panel files the result per ISP (only when the server answered with its own name). A filtered REALITY SNI can be switched to a spare that worked there and suits REALITY (TLS 1.3 + h2, checked from the server): by the admin, or by itself when reality_sni_auto is on (_v180). GET/PUT clean-ip/reality/, POST clean-ip/reality/<id>/switch/ (super admins)._

* Merge pull request #74 from Plus98ir/feat/clean-ip-scanner. 
  _feat(admin_v2): clean IP scanner — find Cloudflare IPs that work on each ISP and save them for it_

* Feat(clean-ip): full test with a real upload, through a one-day command. 
  _Some ISPs cut a connection after ~1.3 KB of upload. A browser can not test that (it can not pick the TLS name for an IP, and its own handshake is ~0.6 KB), so the page makes a one-day command (curl … | python3 - / irm … | python -). It serves a standard-library Python script that tests each Cloudflare IP with TLS (the CDN domain as SNI) and an upload of the chosen size, then reports the working IPs; the panel saves them for the ISP the report comes from (MaxMind), merged like the page does. The page shows each run as it arrives. The token can only add IPs to one CDN domain, for 24 h._

* Feat(admin_v2): clean IP scanner — find Cloudflare IPs that work on the admin's ISP and save them for that ISP. 
  _The panel's server is abroad and can not test the internet in Iran, so the scan runs in the browser of whoever opens the page: random IPs from Cloudflare's ranges, a TLS request to each (a quick TLS error = the IP answers, no answer = blocked; checked against a real upload test: 58 of 60 IPs agree). The panel tells the page which ISP it is on (GET clean-ip/network/, MaxMind as for subscriptions), and the best IPs go into a CDN domain's CDN IP field as "IP SHORT" pairs, keeping other ISPs' pairs: Hiddify then gives each user the IPs of their own ISP. Tools › Clean IP scanner._

* Merge pull request #70 from Plus98ir/perf/panel-compression. 
  _perf(haproxy): gzip the panel and cache its hashed build files_

* Enhance routing configuration with caching and compression. 
  _Updated compression types and added static file caching rules._

* Perf(haproxy): gzip the panel's text responses and let browsers keep the hashed build files. 
  _Admin V2's main bundle (1.35 MB) was sent uncompressed with Cache-Control: no-cache, so every visit downloaded it again; on a slow connection the panel's few request threads were held by these files. Text is gzipped now, and the build's hashed files (static/admin-v2/assets, monaco/<hash>/) are cached as immutable. The live channel (text/event-stream) is not compressed._

* Merge pull request #78 from Hiddify-Official/feat/donation-wallets. 
  _feat(donation): one wallet list, new addresses, clearer dialog_

* Feat(donation): one wallet list, new addresses and a clearer donate dialog. 
  _The wallet addresses were copied into the Donation.description text of
every language, and five of the seven copies still listed old wallets.
The classic modal's TON copy button also copied another address than the
one it showed.

- The wallets live once in hutils/donation.py (Bitcoin, Tether BEP20,
  Tron, Litecoin, Gram/TON); the translations only mark where they go.
  The admin_v2 menu sends them as data and the classic modal renders them
  from the same list.
- The donate dialog shows each coin's icon, its network, the full
  address with a copy button beside it, a QR code, and a hint to send
  only on the shown network.
- A catalog compiled before this change still has the old list in its
  text: the dialog drops it and shows the new list in its place._

* Introduced a users_only parameter to quick_apply_users to optimize user updates without reloading xray. 

* Merge pull request #60 from Plus98ir/fix/bot-links. 
  _fix(telegram): give the same user and subscription links as the panel_

* Fix(telegram): give the same user and subscription links as the panel. 
  _The bot built its own links: the user page had no #<name> and the subscription was auto/ with no name, unlike the links the panel copies. Now the user page is <home>#<name>, the subscription <home>sub/?asn=unknown#<name> and the Hiddify import uses <home>#<name>. The Mini App buttons keep the bare page URL (Telegram adds its own data after #)._

* Merge pull request #61 from Plus98ir/fix/user-apps-api. 
  _fix(user api): app list failed on iOS and "all"; v2rayN shown as V2RayNG_

* Fix(user api): app list failed on iOS and "all"; v2rayN shown as V2RayNG. 
  ___get_loon_app_dto() returned nothing, so the iOS list and platform=all failed validation (None in list[AppSchema]). v2rayN used the v2rayNG title and got no icon. The Linux check had an operator-precedence mistake._

* Merge pull request #63 from Plus98ir/fix/full-width. 
  _fix(admin_v2): pages take the whole width on wide screens_

* Fix(admin_v2): pages take the whole width on wide screens. 
  _Sakai's rule pinned .layout-main to 1504px and centered it above 1960px, so 2K/4K screens showed large empty sides._

* Merge pull request #65 from Plus98ir/fix/sub-domain-order. 
  _fix(sublink): the subscription follows the Domains page order_

* Fix(sublink): the Domains page order had no visible effect on the subscription. 
  _The Domains page says the first domain comes first in configs, but the list was grouped by
proxy, so reordering domains only moved links inside each proxy's group; proxies came in the
database's order, ignoring their sort_order. Profiles now go domain by domain (in the page's
order), each domain's proxies by sort_order; IP-mode and no-inbound proxies, which merge
their domains, stay whole at their first domain.
Checked: the same 146 links (set diff empty), now following the domain order; Hiddify 4.1
and 5.0 profiles parse._

* Merge pull request #66 from Plus98ir/fix/dark-mode-css. 
  _fix(admin_v2): two dark-mode rules applied to the whole page_

* Fix(admin_v2): dark mode turned the whole page's text green / avatar-colored. 
  _In scoped CSS, ":global(.app-dark) .x" compiles to ".app-dark {}": Vue drops what follows :global(). Opening the dashboard (TrendChip) set color: green-400 on <html class=app-dark>, and the admins page set the avatar color. Writing the ancestor as is keeps it unscoped and the rest scoped._

* Merge pull request #59 from Hiddify-Official/feat/nodes-page-few-nodes. 
  _feat(admin_v2): make the nodes page useful with only a few nodes_

* Feat(admin_v2): make the nodes page useful with only a few nodes. 
  _With up to three nodes the page left most of the row empty and hid each
node's numbers behind "More information".

- Each card shows its details (usage report, today's traffic and online
  users, last message each way) inline when there are three nodes or fewer.
- An "Add node" tile fills the empty space in the row.
- The summary bar adds today's traffic and online users of all nodes._

* Config health: a subscription that could not be fetched (a reload right then) is tried once more. 

* Config health: the second chance runs the subscription again (rerun() needs the page's form of each config) 

* Config health: test a failed config once more 30 s later (the cores reload when a domain is saved or configs are applied) 
  _A check that ran while an admin saved a domain reported every config of that domain as broken (tested on a panel: 42 Cloudflare configs failed during the reload, 0 a minute later). Only configs that fail twice are reported._

* Feat(dashboard): config health card (each app's working configs, the broken ones, Check now) 

* Config health: test through Cloudflare's 204 (not Google, often sent through WARP), two requests per config, skip the status line. 

* Feat(config-health): test every config of the subscription from the server every 6 hours. 
  _Runs the config tester on one active user's subscription as the Xray apps and the Hiddify app get it, keeps the last result (GET/POST /api/v2/admin/config-health/, super admins) and tells the super admins on Telegram when configs break that worked before. A config that fails from the server itself never works for anyone._

* Merge pull request #58 from 2Grey/fix/legacy-admin-redirect-path. 
  _fix(admin): preserve proxy path in legacy redirects_

* Fix(admin): preserve proxy path in legacy redirects. 



## v14.0.5 (2026-10-20)

#### Other

* Chore: update subproject reference in user_front to latest commit. 



## v14.0.4 (2026-10-20)

#### Other

* Feat(network): add fallback fake sites for decoy domains and enhance random domain selection logic. 

* Feat(backup): enhance Telegram backup captions with HTML formatting and clickable links. 

* Feat(backup): introduce backup retention policy and enhance backup functionality. 

* Feat(protocols, settings): enhance hover behavior for reinstall indicators and add Persian font support. 

* Merge branch 'dev' of github.com:hiddify/hiddifypanel into dev. 

* Merge pull request #54 from saeed-jalilian/feat/shared-cert-prefer-ip-proxy-domain. 
  _feat(tls): prefer the cert of a domain with an IP-based proxy attached as the shared cert_

* Feat(tls): prefer the cert of a domain that has an IP-based proxy attached as the shared cert. 

* Fix(tls): do not pick a subscription-only domain's cert as the shared cert of IP-based proxies. 

* Merge pull request #50 from davodm/fix/wireguard-server-ipv4-only. 
  _fix(wireguard): skip IPv6 in the server config when the kernel has no IPv6_

* Fix(wireguard): skip IPv6 address, ip6tables and peer IPv6 when the kernel has no IPv6. 
  _wg-quick failed with 'ipv6: IPv6 is disabled on this device' on IPv4-only
servers (disable_ipv6=1), leaving hiddifywg down. Gate the IPv6 parts of the
server template on ctx.hconfig.ipv6_enabled, like haproxy/xray/rpxy-l4 do._

* Merge pull request #55 from 2Grey/fix/admin-legacy-navigation. 
  _fix(admin): resolve missing legacy navigation links to Admin V2_

* Fix(admin): resolve absent legacy navigation views to Admin V2. 

* Merge pull request #56 from 2Grey/fix/telegram-broadcast-multipart. 
  _fix(telegram): preserve multipart data when sending broadcasts_

* Fix(telegram): send broadcast text and images as multipart. 

* Merge pull request #57 from 2Grey/fix/users-last-online-timezone. 
  _fix(users): include timezone offsets in last-online timestamps_

* Fix(users): include UTC offsets in last-online timestamps. 



## v14.0.3 (2026-10-20)

#### Other

* Merge branch 'dev' of github.com:hiddify/hiddifypanel into dev. 

* Feat(admin): implement legacy dashboard redirection in debug mode. 

* Feat(apply): enhance quick_apply_users to handle domain changes. 

* Feat(admin): implement legacy dashboard redirection in debug mode. 



## v14.0.2 (2026-10-18)

#### Other

* Fix(proxy): ensure download leg handling for non-xHTTP transports. 

* Refactor(finalmask): streamline finalmask handling in templates. 

* Feat(telegrambot): improve admin and user linking logic. 

* Feat(platform): enhance VLESS and HTTPUpgrade support for Mihomo compatibility. 
  _- Updated VLESS protocol handling to include additional app versions and features.
- Improved error messaging for VLESS encryption requirements based on Mihomo version.
- Enhanced HTTPUpgrade compatibility notes for Mihomo 1.19.32 with Xray.
- Refactored finalmask handling in templates to treat it as an object instead of a string._



## v14.0.1 (2026-10-18)

#### New

* Add search for user in config tester. 

#### Fix

* Redirect to another domain after status. 

* Edit button in ssh. 

* Error of mtproxy when no domains exist. 

* Download in sublink. 

#### Other

* Feat(telegrambot): enhance bot functionality with user notifications and new API endpoints. 
  _- Updated dependencies in `pyproject.toml` to include `pillow` and `segno`.
- Added a scheduled notification feature for users nearing package expiration.
- Introduced new API resources for Telegram app integration.
- Refactored existing bot handlers and removed deprecated response handling.
- Improved user and admin interaction through enhanced command handling and status updates._

* Improve telegram bot support. 

* Fix(apply): improve scroll behavior to ensure run panel visibility. 

* Feat(apply): streamline certificate refresh process across components. 
  _- Replaced commander calls with hiddify.quick_apply_users() for refreshing core configurations after certificate changes.
- Ensured immediate application of changes in DomainAdmin and domains_page_api.
- Added a dedicated function to handle core updates after domain modifications._

* Refactor(crypto): update SSH key generation to use temporary directory and remove DSA key type. 



## v14.0.0 (2026-10-18)

#### New

* Advancced cert management and deprecate nginx and acme.sh. 

* Add telegram webproxy. 

* Add quick enable of disabled settings. 

* Improve node registeration. 

* Add advanced config tester. 

* Add wiregaurd proxy generator. 

* Add snell v4 and v6. 

* Add domain ip in domain wizard. 

* Add wiregaurd by hiddify-core. 

* Add extra information in the user row, refactor mobile view, add easy click for change limits, add persian date for exact finish time. 

* Add state for filters in views, make a deep link, fix tranlstions. 

* Add finalmask support. 

* Add psiphone and tor backend. 

* Add cpu   core and ram info in the chart. 

* Rewrite log and actions into new interface. 
  _- Removed the old ActionsView component and integrated its functionality into the new ApplyView.
- Introduced a new API for managing apply actions, including apply, install, update, and restart.
- Added components for displaying logs and running actions with live progress tracking.
- Updated routing to redirect from the old actions path to the new apply path.
- Enhanced user interface with new dialogs for log viewing and action confirmation.
- Improved error handling and user feedback mechanisms throughout the apply process._

* Add domain ip extraction. 

* Redesign backup page, integrate Telegram bot functionality. 
  _- Added support for linking admin accounts to the panel's Telegram bot, enhancing communication and notifications.
- Introduced a new component for Telegram connection management, including a QR code for easy linking.
- Implemented a prompt for admins to connect their Telegram accounts if not already linked.
- Updated the admin account view to display the Telegram connection status and provide options for reconnection.
- Enhanced the dashboard with a Telegram prompt for better user engagement.
- Added API support for managing Telegram connection states and notifications.
- Improved translations and UI elements to reflect the new Telegram features._

* Add domain management features. 
  _- Introduced a new API for managing domains, including listing, creating, updating, and deleting domains.
- Added components for domain management, including a wizard for adding domains and a dialog for editing existing domains.
- Implemented certificate progress tracking and validation for domain certificates.
- Enhanced user experience with improved form validation, error handling, and feedback mechanisms.
- Added support for custom proxy configurations and domain-specific settings.
- Updated translations and UI elements to reflect new domain management features._

* New user management features. 
  _- Added user management view and dialog components for creating and editing users.
- Introduced API integration for user data handling, including listing, creating, updating, and deleting users.
- Implemented user status and mode management with appropriate UI elements.
- Enhanced user experience with improved form validation and feedback mechanisms.
- Added support for sharing user links via QR codes and direct links._

* New admin page. 

* Better integration with the old panel. 

#### Fix

* Domain bug. 

* Reality L7 inbounds, cert/fingerprint defaults, xray driver and admin limits Attach Reality domains to xhttp/grpc server proxies, add _v176 to re-enable Reality after upgrade, default Reality fingerprint to chrome when uTLS is none, read xray protocol/flow from generated config, and fix restore migrations, sublink commas, haproxy proto None, and admin user-limit checks on enable. 

* Cert issue in sni domain. 

* Prevent admins from being their own parent in admin hierarchy and update validation logic for self-patching. 

* Admin permission security issue. 

* Enhance HAProxy certificate handling by ensuring proper addition to crt-list and refining payload processing in haproxy_api. 

* Deleted user username. 

* Implement watchdog mechanism for stream monitoring and enhance log handling during panel restarts. 

* Enhance URL handling for IPv6 addresses and improve logging error handling. 

* Update log file paths for consistency across the application. 

* Update lock file path in apply_api.py for consistency. 

* Update ECH configuration handling in TLS templates to prioritize extra configuration over existing settings. 

* Add remarks for usage and package status in proxy configuration template. 

* Websocket host issue. 

* Backup from 13 to 14. 

* Adding a domain fails with "Cloudflare error: Missing required argument: 'ttl'" whenever a Cloudflare token is set. 

* IP-mode proxies (Hysteria2/TUIC) ignore the domain's "Resolve IP" switch. 

* Update IP-based proxy logic to include relay domains for validation. 

* Telegram proxy. 

* Update admin menu structure to include tools at the end for consistency. 

* Bug. 

* Bug. 

* Handle exceptions when retrieving Telegram usage data in TelemtApi. 

* Hiddify version. 

* Hysteria and vmess quic. 

* Update TLS handling in _skips_hiddify_client_tls to include 'snell' protocol for improved compatibility. 

* Remove unused ports settings. 

* Improve form validation logic to allow unrelated changes when some fields are invalid. 

* Content-hash the prebuilt Monaco copy. 
  _Same cache problem the content-hashed Vue assets fix: the prebuilt Monaco is copied
from node_modules outside Rollup, so its files kept stable URLs (monaco/vs/...).
After an update a browser or CDN cache could keep serving an old loader.js /
workerMain.js against the new UI and break the editor.

- vite.config.ts: copy the tree to monaco/<content-hash>/vs — the hash covers exactly
  the files that are copied, so it is stable across builds and only changes when the
  Monaco content does
- v2_view.py: resolve the hashed directory (falls back to monaco/vs for old builds)
  and pass it to the shell
- admin_v2.html: expose it as window.__MONACO_BASE__
- monaco.ts: prefer window.__MONACO_BASE__ over deriving the path from the entry chunk
  URL; dev flow and old-shell fallback unchanged
- client.ts: declare __MONACO_BASE__ on Window_

* Uuid not restored. 

* Ipv6 enabled configs. 

* Change bug. 

* Outbound issue. 

* Domain menu issue. 

* Fix panel icon in v2 paths. 

* Add node configs to sing-box based clients. 

* Cli. 

* Update finalmask handling in VLESS template. 
  _- Modified the VLESS template to ensure the finalmask is processed as compact JSON when set.
- Corrected the assignment of the flow parameter to properly assign the value from the configuration._

* Simplify CDN IP validation in domain management. 
  _- Removed unnecessary condition for CDN IP in the DomainDialog component, ensuring it is displayed for all non-sublink modes.
- Updated backend validation to eliminate the restriction on specifying CDN IP for direct mode, improving flexibility in domain configuration._

* Quick  setup. 

* Improve error handling in Node API client. 

* Node api. 

* Backup. 

* Update TLS layer handling for raw HTTP, WS, and HTTPUpgrade transports. 

* Pass base_cmd to background commander thread so commands actually run. 
  _When commander() is called with run_in_background=True (the default), the
background command was never executed. The thread was created as
`threading.Thread(target=cmd_in_back, daemon=True)` without forwarding the
constructed `base_cmd`, so `cmd_in_back(cmd)` was invoked with no arguments
and raised before subprocess.Popen ever ran:

    TypeError: cmd_in_back() missing 1 required positional argument: 'cmd'

Forward base_cmd to the thread via args=(base_cmd,)._

* Sanitize shell/subprocess call in run_commander.py. 
  _The run_commander
Addresses CWE-78_

* Standardize default TLS layer to 'http' across various components. 

#### Other

* Feat(apply): enhance admin link handling and UI updates. 
  _- Introduced AdminLink interface to manage secure and insecure admin URLs.
- Updated RunPanel component to display admin links with security status and copy functionality.
- Improved user experience by showing relevant links after apply/install processes.
- Added translations for new link-related messages in multiple languages._

* Feat(apply): implement preferred admin link redirection after domain changes. 

* Fix(apply): update CORS handling in ApplyLogApi to ensure proper log access during apply/install processes. 

* Feat(apply): add skipConfirm prop to ApplyRunDialog for immediate execution. 

* Refactor(domains): improve RTL handling and enhance DomainDialog functionality. 

* Enhance telegram links rendering. 

* Feat(config-tester): update application selection and user agent handling. 
  _- Replaced user agent selection with an application dropdown in the ConfigTesterView for better clarity.
- Introduced a new App type to manage application-specific user agents.
- Updated backend API to validate the selected application and adjust request handling accordingly.
- Enhanced user agent parsing logic to accommodate new application formats and improve error handling for unsupported formats.
- Added translations for the new application selection feature in English and Persian._

* Sync haproxy ssl during upgrade. 

* Feat(proxy_v3): enhance rendering and parsing logic for Clash YAML and JSON. 
  _- Improved the handling of Clash YAML by adding structured parsing to display pretty JSON in the preview dialog when JSON5 parsing fails.
- Updated the RenderSectionResult model to include a skip_reason for better context on skipped sections.
- Enhanced the rendering logic to conditionally return pretty JSON or the original rendered output based on formatting checks.
- Adjusted the HTTP upgrade template to conditionally skip based on the server core type._

* Feat(admin): enhance user management limits with new activation checks. 
  _- Added methods to check for room to activate users and handle user limits more effectively.
- Updated validation logic in UserAdmin and API endpoints to respect max active users during user activation.
- Improved clarity in method documentation for better understanding of user limit constraints._

* Refactor(ui): update layout padding and enhance DomainDialog component functionality. 
  _- Adjusted padding properties in the main layout SCSS for improved responsiveness.
- Modified DomainDialog to use async component loading for Json5Editor and added mobile menu handling on dialog visibility changes.
- Updated DomainsView to conditionally render DomainDialog based on visibility state.
- Enhanced translations for showDomainsHint in English and Persian to clarify usage requirements._

* Fix(admin): improve user limits handling by adding default values for max users and active users checks. 

* Feat(proxy_v3): implement allowlist for panel routing to bypass blocking for specified domains and IPs. 

* Fix(proxy_v3): update user agent parsing and protocol templates for Hiddify and Sing-box compatibility. 

* Fix(proxy_v3): enhance REALITY download leg validation logic. 

* Refactor(node): streamline panel mode handling and remove deprecated configurations. 
  _- Introduced a new `panel_mode` function to determine the current panel mode (`child`, `parent`, or `standalone`).
- Updated references in various modules to utilize the new `panel_mode` function.
- Removed deprecated configurations related to panel mode from `ConfigEnum` and adjusted related logic in admin views and API endpoints.
- Enhanced clarity and maintainability of the codebase by consolidating panel mode checks._

* Feat(proxy_v3): add Hysteria and Tuic protocol templates with SNI and insecure handling. 

* Fix(proxy_v3): handle optional WireGuard client configuration gracefully. 

* Fix(proxy_v3): update VLESS encryption handling for Hiddify 5+ compatibility. 

* Fix(proxy_v3): ensure tls_layer function is called in xhttp templates for consistent TLS handling. 

* Refactor: update desktop detection logic to use matchMedia for improved responsiveness. 

* Merge branch 'dev' of github.com:hiddify/hiddifypanel into dev. 

* Merge pull request #48 from Survivor-viper/fix/xhttp-download-tls-http. 
  _fix(proxy_v3): keep TLS on xhttp download leg when download_tls_layer is empty (#5591)_

* Refactor tls_layer assignment to use default filter. 

* Fix(proxy_v3): keep TLS on the xhttp download leg when download_tls_layer is empty. 
  _hiddify-core/client/tls/tls_http.j2 used `tls_layer is defined` to decide
whether the layer was passed in. It is included from the xhttp stream with
`{% with tls_layer=proxy.download_tls_layer %}`, and download_tls_layer=None
means "same as upload". `{% with tls_layer=None %}` still makes the variable
*defined*, so `None or "http"` gave "http" and the download leg was rendered
with no tls block -- a plain-HTTP stream to port 443 that breaks immediately
(the "closed pipe" download handshake error in #5591).

Use a truthiness test, matching the sublink template
(sublink/uri/security/tls_http.j2), so None falls back to the upload layer._

* Refactor: simplify download handling in proxy domain validation and update xHTTP download settings template for improved clarity. 

* Feat: implement download/upload differentiation in proxy configurations, enhancing xHTTP settings and TLS handling for improved domain management. 

* Feat: add Tor availability check and user notifications in outbound configurations, enhancing error handling and user experience. 

* Feat: enhance support for Trojan in REALITY configurations, updating documentation and validation logic for proxy protocols. 

* Feat: enhance ECH support in proxy configurations, adding per-domain toggles and improving TLS handling for various protocols. 

* Chore: update subproject reference for user front module. 

* Feat: integrate user front module with build and deployment processes, including new Makefile targets and GitHub Actions updates. 

* Refactor: introduce PEM normalization for certificate handling and improve error logging in write_files. 

* Feat: add support for Clash Meta configuration in proxy_v3, including new types and templates for client protocols and streams. 

* Proxy_v3: the reality_enable setting has no effect (domain_mode_config_map key never matches the stored modes) 

* IPVar.merge drops addresses, so the domain field cdn_ip (forced connect address) has no effect in 13.x. 

* API v2: users of sub-admins appear in GET /admin/user/ but GET/PATCH/DELETE /admin/user/<uuid>/ on them return 403. 

* Feat: implement broadcast feature for sending messages via Telegram bot, including UI components for message composition and recipient selection. 

* Add  new wiregaurd output model .conf and .zip in case of multiple. 

* Proxy_v3 small correctness bugs: alpn_helpers treats {} as "filter by hconfigs", and TemplateVersion.__ne__ against a string is always True. 

* Usage accounting: node usage is silently dropped when the usage lock is busy, and admin/update_user_usage runs the accounting without the lock. 

* Usage drivers lose or mislabel traffic: WireGuard rx/tx swapped and counter resets dropped, telemt zero baseline discarded, 

* Tls_store_sync: a valid Let's Encrypt IP certificate for an IPv6 address gets valid_cert=False (SAN compared as a string) 

* "Online yesterday" and average online stats are multiplied by the number of nodes. 

* Feat: implement UniqueTags class for managing unique outbound tags across configurations. 

* Support short link directly in haproxy deprecating nginx. 

* Deprecate custom port for tls and http globally. 

* Feat: improve ApplyView functionality by adding run panel visibility control and enhancing user interaction with running actions. 

* Feat: enhance Telegram proxy functionality by adding support for web proxy and updating configuration options. 

* Feat: add PWA support with manifest and icons for improved installation experience. 

* Feat: implement PWA installation dialog and related functionality for enhanced user experience. 

* Refactor: streamline Telegram web proxy template logic for improved clarity and efficiency. 

* Feat: enhance UI components with improved layout and accessibility features and fix domain download mode. 

* Feat: enhance Telegram proxy support with new templates and configuration updates. 

* Feat: add Persian translations for SSH terminal features and related utilities. 

* Feat: implement read-only mode for users and admins on child nodes, enhancing UI and API to reflect parent panel management. 

* Feat: add Cloudflare ECH configuration support in TLS templates. 

* Imporove telegram proxy support. 

* Speed up apply configs, and cache managemnt. 

* Move firewall to database. 

* Speed up dump config by removing users. 

* Feat: implement node synchronization status tracking and UI components. 

* Feat: enhance Telemt API integration with new user management and usage tracking. 

* Feat: enhance WebSocket handling and improve translations. 

* Feat: new add advanced full ssh terminal with file editor and multi ssh command runner. 
  _- Integrated SSH functionality into the admin interface, allowing users to connect and manage SSH sessions.
- Implemented SSH session handling with support for terminal output and command execution.
- Added components for file editing and output viewing, enhancing user experience.
- Introduced a vault for securely storing SSH credentials and configurations.
- Updated routing to include SSH-related endpoints in the ASGI application.
- Enhanced the admin menu to include SSH tools and utilities._

* Refactor: update deleted filter checks to use isnot for consistency. 

* Feat: big change, stream support no more pulling.... 
  _- Added ASGI support by introducing `hiddifypanel/asgi.py` and `hiddifypanel/asgi_types.py`, allowing the application to handle asynchronous requests.
- Updated WSGI application to use the new ASGI builder.
- Implemented live channel features in the admin interface, including a new `live.ts` module for managing live data streams and a `WsTestDialog` component for WebSocket testing.
- Enhanced database connection pooling options to improve performance under load.
- Updated dependencies in `pyproject.toml` to include `a2wsgi`, `websockets`, and `httpx` for better async handling._

* Make sure the proxies will not have a same tag in the server side. 

* Feat: enhance user registration handling in node-parent communication. 
  _- Introduced a new API endpoint for registering users that the parent does not have, allowing for improved synchronization of user data.
- Updated the registration logic to handle user UUIDs more effectively, ensuring that only missing users are sent to the parent.
- Enhanced the RegisterInputSchema to include user UUIDs and added corresponding handling in the registration process.
- Improved error handling and logging for user registration failures, aiding in better monitoring and debugging._

* Make async node registration. 

* Feat: improve node registration error handling and logging. 
  _- Enhanced the NodeRegisterError class to include additional context such as the side of the failure and registration ID.
- Updated error handling in the registration process to provide more detailed feedback on failures.
- Introduced a new logging mechanism to trace registration steps and errors, aiding in debugging and monitoring.
- Added translations for new error messages related to node registration failures._

* Feat: enhance parent-child registration logic in RegisterWithParentApi. 

* Feat: implement config tester job management and event handling. 
  _- Added new API endpoints for managing config tester jobs, allowing for job creation, retrieval of events, and cancellation.
- Introduced types for events and job pages to standardize data handling.
- Enhanced the config tester functionality to support asynchronous job processing and event streaming.
- Updated the client-side components to handle editable JSON structures and improved user interaction in the config tester view._

* Feat: add logging for user application and command execution in hiddify.py and run_commander.py. 

* Better persian support. 

* Fixed bug in progress bar persian. 

* Feat: enhance domain ordering and caching in various components. 

* Feat: implement WARP address filtering in IP retrieval functions. 

* Faster outbound apply. 

* Faster apply users. 

* Feat: add support for Telegram MTProxy (telemt) including configuration and server driver. 

* Feat: add ApplyRunDialog component for running apply actions in a dialog; update ApplyNotice to utilize the new dialog and enhance user experience. 

* Feat: improve backup functionality for custom proxies, including unique slug generation and restoration of built-in proxies. 

* Refactor: replace CodecPanel with LiveCodecPanel for real-time encoding/decoding; remove unused CodecPanel component. 

* Merge branch 'dev' of github.com:hiddify/hiddifypanel into dev. 

* Merge pull request #44 from AnonymousContributorAlpha/vite-monaco-hash. 
  _fix: content-hash the prebuilt Monaco_

* Feat: enhance Persian support; enhance user metrics with active user count. 

* Add admin customizable lang. 

* Restore trojan httpupgrade and xhttp. 

* Feat: add reset all functionality for built-in proxies and enhance custom proxy list view with quick filters. 

* Link public port to the custom proxy. 

* Redirectspeed test page. 

* Improve domain page. 

* Ignore vless encryption from old backup. 

* Speed up domain page. 

* Refactor: update TCP/UDP port handling in ClientProxyDomainVar. 
  _- Enhanced the logic for determining TCP and UDP ports based on proxy mode.
- Clients now connect to the domain's gateway port when applicable, improving routing accuracy._

* Refactor: r update public ports logic. 
  _- Updated the all_public_ports function to include SSH in the list of custom proxies.
- Adjusted related comments and cleaned up unused code in various files._

* Improve backup / restore. 

* Feat: enhance domain validation in settings. 
  _- Added a new function `domains_taken_by_others` to check for domain names already in use, excluding the current fake-domain row.
- Updated the domain validation logic in `SettingAdmin.py` to utilize the new function, improving the accuracy of domain availability checks._

* Merge pull request #39 from AnonymousContributorAlpha/vite-manifestation. 
  _refactor: add vite manifestation_

* Refactor: add vite manifestation. 

* Merge pull request #38 from AnonymousContributorAlpha/icon-v2. 
  _fix: fix panel icon in v2 paths_

* Merge pull request #42 from AnonymousContributorAlpha/node-configs. 
  _fix: add node configs to sing-box based clients_

* Merge pull request #41 from AnonymousContributorAlpha/user-id. 
  _feat: added user id to admin/v2 users page_

* Feat: added user id to admin/v2 users page. 

* Feat: add finalmask support to hiddify-core. 
  _- Included the finalmask snippet in endpoint_general, outbound_general, outbound_v2ray, outbound_xhttp, and wireguard templates to enhance JSON output.
- Created a new finalmask.j2 snippet to conditionally include the finalmask based on proxy domain settings and Hiddify Core version._

* Feat: implement custom JSON outbounds for hiddify-core and xray. 
  _- Added support for custom JSON configurations in the Outbounds API, allowing admins to define hiddify-core outbound, endpoint, and xray outbound objects.
- Introduced new outbound modes: 'core_outbound', 'core_endpoint', and 'xray_outbound'.
- Enhanced the OutboundDialog component to handle custom JSON input, including validation and example configurations.
- Updated backend models and API to store and validate custom JSON entries, ensuring they are checked by the respective core before saving.
- Improved UI translations to accommodate new features and provide guidance on custom JSON usage._

* Feat: implement threading for user application process. 
  _- Introduced a new threading mechanism to handle the `quick_apply_users` function, allowing multiple requests to queue while the command is running.
- Added a worker function to manage the application of user changes, ensuring that the latest changes are always applied.
- Implemented logging for error handling during the user application process to improve debugging and monitoring._

* Feat: update backup restore options and UI components. 
  _- Renamed `override_root_admin` to `replace_owner_admin` in the RestoreOptions interface to clarify functionality.
- Updated RestoreCard component to reflect the new option name and adjusted associated UI elements.
- Enhanced translations for both English and Persian to include new terms related to the owner replacement feature.
- Modified backend API to accommodate the updated restore options, ensuring consistent behavior across the application._

* Feat: introduce fake-TLS domain management for Telegram and ShadowTLS. 
  _- Added support for new fake-TLS modes: 'telegram', 'shadowtls', and 'ssfaketls' in the domain management system.
- Implemented logic to ensure only one instance of each fake-TLS domain can exist per node.
- Updated UI components to reflect the new fake-TLS modes and their restrictions.
- Enhanced backend validation to manage fake-TLS domains effectively, ensuring they sync with their respective settings.
- Improved translations to include new terms related to fake-TLS functionality._

* Refactor: streamline SNI handling and domain fronting logic. 
  _- Removed redundant ECH public name extraction from SNI handling in `sni_host_server_extractor` and `DomainIPVar` class.
- Introduced a new helper function `_is_fronting` to encapsulate domain fronting logic, improving code clarity and maintainability.
- Updated references to ECH information to ensure consistent handling across domain processing functions._

* Feat: enhance ECH handling and domain detection. 
  _- Introduced a new function `get_domain_ech_info` to retrieve ECH configuration for Cloudflare-hosted domains.
- Updated existing functions to utilize the new ECH retrieval method, improving accuracy in ECH information handling.
- Enhanced the public name extraction from ECH configurations for better SNI management.
- Modified templates and proxy configurations to support the new ECH structure, ensuring compatibility across components._

* Feat: enhance UI components and styles for better user experience. 
  _- Updated the topbar background to a dynamic gradient for a more vibrant appearance.
- Replaced Select components with Listbox for improved filtering and selection in various popovers.
- Introduced utility functions for color styling of tags based on core and protocol types, enhancing visual organization.
- Added autofocus functionality to input fields in popovers for improved accessibility and user interaction._

* Feat: add 'add_limits' bulk action for user management. 
  _- Introduced a new bulk action to add data limits and days to selected users.
- Updated the API to handle the new 'add_limits' action, allowing for flexible user management.
- Enhanced the UsersView component with a dialog for inputting limits, improving user experience.
- Updated translations to include new terms related to the 'add_limits' functionality._

* Feat: implement tagging system for users. 
  _- Introduced a new tagging feature allowing admins to assign colored tags to users for better organization and identification.
- Added API endpoints for creating, updating, and removing tags, as well as assigning tags to users.
- Implemented UI components for tag selection and management within user forms and views.
- Enhanced user experience by integrating tag filters and displays in user lists and detail views.
- Updated database models to support tag functionality, ensuring data integrity and efficient retrieval._

* Feat: add log clearing functionality in LogViewerDialog. 
  _- Implemented a clear button to remove log entries, with confirmation dialog and success/error toast notifications.
- Enhanced user experience by allowing users to clear logs directly from the Log Viewer interface._

* Feat: enhance outbound management and synchronization. 
  _- Introduced new functions for managing outbounds, including applying changes from the parent panel and syncing outbound configurations.
- Updated the AdminUser and User models to include preferred outbound slugs, allowing for better outbound management.
- Enhanced the API to support outbound operations, ensuring that outbounds are managed centrally by the parent panel.
- Added new methods for exporting and importing outbound configurations, improving synchronization between parent and child panels.
- Updated database migration scripts to accommodate changes in outbound structure and ensure compatibility.
- Improved translations to reflect new outbound management features._

* Feat: add default outbound management for admins. 
  _- Introduced new functionality for setting a default outbound for admin users and their sub-admins.
- Updated API to handle default outbound settings, including retrieval and application of inherited outbounds.
- Added a new component for selecting default outbound options in the admin form.
- Enhanced admin views to display and manage default outbound settings.
- Improved validation and error handling for outbound selections.
- Updated translations to reflect new outbound management features._

* Support any ports for domains. 

* Feat: implement admin alias functionality. 
  _- Added support for admins to sign in using an alias (username) instead of UUID, enhancing user experience and security.
- Introduced strong password requirements for alias usage, ensuring better account protection.
- Updated admin management API to handle alias creation and validation.
- Enhanced admin views to display and manage aliases, including error handling for invalid aliases.
- Implemented frontend components for alias input and validation, improving user feedback and interaction.
- Added translations and UI updates to reflect the new alias feature._

* Feat: add additional configuration management for admins. 
  _- Introduced a new component for managing additional configurations for admins and their users.
- Updated API to support saving and retrieving additional configurations.
- Enhanced admin and user views to display and edit additional configurations.
- Improved validation and error handling for configuration inputs.
- Added translations for new configuration features._

* Add new outbound manager. 

* Feat: update translations. 

* Feat: enhance proxy configuration and editor functionality. 
  _- Updated the default form for custom proxy settings to use context variables for better data handling.
- Improved the Jinja and JSON5 editors by adjusting their minimum height for better usability.
- Introduced a new utility function to dynamically fit the editor's height to its content.
- Enhanced transport TLS support for raw TCP and gRPC in the proxy validation logic.
- Updated translations to include new HTTP terminology and improved language support.
- Added new presets for raw VLESS over REALITY, streamlining the configuration process for users._

* Fixxray. 

* Feat: add quick setup feature for streamlined initial configuration. 
  _- Introduced a new quick setup process to guide users through initial configuration steps.
- Added components for language selection, password setup, domain management, and finalization.
- Implemented API interactions for quick setup state management and domain handling.
- Enhanced user experience with improved error handling and feedback mechanisms throughout the setup process._

* Add copy qr  code  image. 

* Feat: enhance domain mode handling and reality support. 
  _- Updated domain mode options to include selected modes for both upload and download configurations.
- Introduced functions to determine if domain modes are editable based on proxy settings.
- Improved transport TLS support for reality domains, allowing raw HTTP to utilize TLS effectively.
- Enhanced category management in custom proxy presets to include new reality categories without removing admin-set categories.
- Refactored proxy combination logic to support reality domains across various transport types._

* Make random choice of ips. 

* Feat: enhance node removal functionality and improve user feedback. 
  _- Updated the `remove` method in the nodes API to return a boolean indicating whether the node successfully unlinked from its parent.
- Modified the `confirmRemove` function in `NodesView.vue` to provide user feedback based on the unlinking status, displaying appropriate success or warning messages.
- Added a new `UnregisterParentApi` to handle the scenario where a node is removed by its parent, allowing it to switch to standalone mode.
- Improved the handling of domain normalization in the `Domain` model to prevent duplicate entries during sync operations._

* Feat: implement TLS fragment support in proxy templates. 

* Feat: enhance user login handling and database isolation. 
  _- Added logging for failed updates to the last_online timestamp of admin users during login, improving error tracking.
- Implemented a try-except block to handle potential database update conflicts gracefully.
- Introduced READ COMMITTED isolation level for MySQL/MariaDB to prevent transaction errors during concurrent updates.
- Updated SQLAlchemy engine options to support the new isolation level, ensuring data consistency._

* Feat: implement legacy action dialog for classic system actions. 
  _- Added a new `LegacyAction` interface and `openLegacyAction` function to manage classic system actions in a dialog.
- Introduced `LegacyActionDialog` component to display actions in an iframe, enhancing user experience.
- Updated various components to utilize the new legacy action handling, replacing direct URL navigation with dialog-based interactions.
- Enhanced translations to support new dialog features._

* Feat: enhance admin menu structure and translations. 
  _- Introduced a new `id` property for `AdminMenuGroup` to facilitate menu grouping.
- Defined a constant `GROUP_ORDER` for consistent menu group ordering (manager, settings, help).
- Refactored `useAdminMenu` to dynamically generate menu groups based on server data and frontend routes.
- Updated translations to include new group labels for better localization support._

* Feat: add plugin for adminV2 translations handling. 

* Feat: integrate Monaco editor with loading state and error handling. 
  _- Added a new plugin to handle the prebuilt Monaco editor, improving performance by avoiding bundling.
- Implemented loading state and error messages in the JinjaTextEditor and Json5Editor components.
- Updated translations for loading and error messages.
- Refactored Monaco setup to ensure it loads only when needed, enhancing user experience._

* Optimise build. 

* Refactor: improve backup functionality in CLI. 
  _- Updated the backup task to use os.path.join for better path handling.
- Changed the backup directory creation to set permissions to 750 for enhanced security.
- Modified file opening to use os.open and os.fdopen, ensuring the backup file is only readable by the panel user._

* Remove admin built data. 

* Add  new node page, and integrate old admin with new admin. 

* Rewrite settings page. 

* Feat: add protocols management feature. 

* Feat: implement node management enhancements and new actions view, only super admin can access nodes panel. 
  _- Added a new `_deny_non_super_admin_on_node` function to restrict non-super admins from managing nodes, improving security.
- Introduced the `ActionsView` component to display available system actions for super admins, enhancing user interface and functionality.
- Updated routing to include a dedicated node home page for child panels, providing a clearer navigation experience.
- Enhanced the `CustomProxyEditorView` to support better name management and user feedback for built-in proxies.
- Introduced new global variables for panel mode and node information to streamline data handling across components._

* Refactor: streamline sync operations and enhance parent notification handling. 
  _- Removed deprecated sync fields from the child node's API, focusing on domain synchronization only.
- Introduced a new mechanism to notify the parent of configuration changes in child nodes, improving responsiveness to updates.
- Updated various admin views to utilize the new notification system for user and configuration changes, ensuring consistency across the application.
- Enhanced error handling and logging during synchronization processes to improve debugging and reliability._

* Verify and check multi node configs. 

* Refactor: improve child model timestamp handling and proxy context management. 
  _- Introduced a new `_touch` method in the `Child` model to manage timestamp updates with better concurrency handling.
- Enhanced error logging for database update failures in the `mark_node_to_parent` and `mark_parent_to_node` methods.
- Refactored proxy context handling in `custom_proxy_validate.py` and `jinja_context.py` to streamline data access and improve clarity.
- Removed legacy code related to `HconfigsAccessor` and `RenderContextAdapter` to simplify the context management logic.
- Increased the default timeout in `jinja_download.py` to improve download reliability._

* Feat: enhance error handling in custom proxy operations. 
  _- Introduced a new `apiErrorMessage` function to format server-provided error messages for better user feedback.
- Updated `duplicateBuiltin` and `save` functions in `CustomProxyEditorView.vue` to utilize the new error handling, improving user experience during API calls.
- Enhanced `CustomProxyListView.vue` to handle errors during proxy duplication with user-friendly notifications.
- Added a new utility function to flatten error details for clearer presentation in the UI._

* Refactor: enhance parent registration and error handling in child node management. 
  _- Improved the registration process to ensure the parent unique ID is validated.
- Implemented upsert logic for parent nodes to prevent 500 errors on re-registration.
- Added exception handling during the registration process to log errors and rollback transactions as needed.
- Updated related methods to accept models instead of dictionaries in bulk registration._

* Improve domain proxy selection. 

* Feat: enhance Telegram bot integration with webhook secret validation. 
  _- Always re-register the bot to ensure it uses the current webhook URL/secret.
- Introduced a `webhook_secret` function to derive the secret token from the bot token.
- Updated the TGBotResource to validate the incoming requests against the webhook secret and content type._

* "Block Iranian sites" does nothing. 

* Fix "Resolve IP" switch. 

* Refactor: enhance domain handling by introducing `has_cdn_ip` and updating logic for server domain retention. 
  _- Added `has_cdn_ip` attribute to `DomainIPVar` to track CDN IP presence.
- Updated the `keeps_dst_server` property to include both `has_server_domain` and `has_cdn_ip`.
- Modified related functions to reflect the new logic for domain expansion based on CDN IPs._

* Feat: add support for XHTTP configurations with different upload and download domains. 
  _- Introduced a new configuration option `xhttp_different_up_down_enable` to allow XHTTP setups with distinct upload and download settings._

* Merge pull request #30 from rezasabourinejad/fix/background-commander-args. 
  _fix: pass base_cmd to background commander thread so commands actually run_

* Merge pull request #37 from anupamme/fix-repo-hiddifypanel-multi-agent-cwe-78-hiddifypanel-panel-run-commander-py. 
  _fix: sanitize shell/subprocess call in run_commander.py (CWE-78)_



## v13.0.3 (2026-09-26)

#### Other

* Custom proxy validation is  now optional as  warning not an error. 



## v13.0.2 (2026-09-26)

#### Fix

* Subadmin access. 

#### Other

* Fix sqlalchemy dependency specifier. 



## v13.0.0 (2026-09-26)

#### New

* Lazyload xtlsapi for lower memory usage. 

* Add new comperhensive dashboard. 

* Add last online node, make singbox  and hiddify core working. 

* Add  multiple proxy selector. 

* Multinode. 

* Multi node. 

* Add get configs from child. 

* Add extra params for domains and users that can be used in custom proxy maker. 

* Add dns protocols. 

* Refactor custom proxy. 

#### Fix

* Update validation for inbound ports in proxy configuration. 
  _Modified the validation logic to require at least one inbound TCP or UDP port for modes that require static ports. Updated error messages to reflect this change, ensuring clearer feedback for users regarding port requirements._

* Wiregaurd. 

* Handle IntegrityError during database commit in set_hconfig function. 
  _Added error handling for IntegrityError when committing changes to the database. If an IntegrityError occurs, the session is rolled back, and the function attempts to update the existing configuration value instead of raising an error._

* Pin apscheduler to <4.0.0 to avoid breaking pre-release. 
  _apscheduler 4.0.0a6 removed the apscheduler.schedulers module that
scheduler.py imports, crashing the app on import when a resolver
picked up the pre-release._

* Cli. 

* User package end date calculation for usage reset logic. 

* Naive quic. 

* Restore domain_strategy for older singbox versions. 

* Wiregaurd bug. 

* Encryption=none for non xray cores. 

* Mieru, wiregaurd, xhttp download settings. 

* Update child sync request to use base URL instead of domain. 

* Parent bug. 

* Parent registration. 

* Default tls_layer in the xray server TLS template. 

* Skip inbound ports and domain binding for no_inbound custom proxies. 

* Treat sub_link_only as a domain mode after dropping leftover DomainTypes. 
  _Queries and APIs still filtered the old boolean column and accepted removed modes like old_xtls_direct and auto_cdn_ip._

* Skip cache flush during apply_users so Apply Config does not kill the panel. 
  _Dumping configs was wiping Redis/Jinja caches even when MODE=apply_users, which restarted the same panel process._

* Return a visible error config when client render fails. 
  _Render errors were only printed, so clients still received an empty body with HTTP 200._

* Round TB usage before formatting subscription remarks. 
  _Jinja applied round(3) to 1000 instead of the usage value, so tiny usage showed up as scientific notation._

* Use HTTP/1.1 ALPN and Accept */* for raw HTTP transport. 
  _Full fake headers plus h2 ALPN broke TCP HTTP obfuscation handshakes._

* Label expanded IPv4/IPv6 endpoints in outbound tags. 
  _When a domain is expanded per IP, tags now include the address family so clients can tell the copies apart, and remark fragments are trimmed of the extra newlines._

* Invalidate v3 Jinja and Redis caches when domains or proxies change. 
  _Subscription output could stay stale for 10–20 minutes after Apply Config because proxy_v3 template maps were never dropped._

* Pin CDN TLS to the edge cert and prefer a stable server IP. 
  _CDN clients were pinning the origin cert while the handshake shows the CDN edge cert. Direct/Reality server addresses also pick a stable IPv4-first IP instead of a random cached A/AAAA mix._

* Keep VLESS flow and encryption on xray core only. 
  _hiddify-core VLESS outbounds were getting xray-only flow/encryption and failing to connect; templates now read ctx.hconfig and emit those fields only for xray._

* Emit Reality client configs from L7 proxies instead of pinning termination. 
  _Reality domains no longer auto-bind xray-reality-termination on the client, so /sub and related endpoints get the matching L7 Reality proxies instead of an empty list._

* Wiregaurd and typing issues. 

* Bug. 

* Singbox issues. 

* Bug. 

* Upgrade. 

* Installation bugs, show errors in dump configs, and fix routing bug. 

* Domains. 

* Redis for wiregaurd and telemt. 

* Reality bug. 

* Ssh key generation when a key type is not availble. 

* Tcp mode. 

* Bugs. 

* Xray  api. 

* Issue in extra params. 

#### Other

* Feat: enhance template variables and improve static asset handling. 
  _- Added new template variables for current server time and date arithmetic in `template_variables.py`.
- Replaced the use of `exec` for dynamic path generation with a static variable for panel assets in `jinja_render.py`.
- Updated Nginx template files to utilize the new `panel_static_dir` variable and improved time handling for configuration links._

* Feat: implement danger confirmation for destructive actions. 
  _- Introduced a new `useDangerConfirm` composable to handle confirmation prompts for destructive actions, enhancing user safety during critical operations.
- Updated various components to utilize the new confirmation method, replacing the previous `useConfirm` implementation.
- Enhanced the dashboard and configuration views to ensure consistent confirmation behavior across the application.
- Added localization support for confirmation messages, improving the user experience in different languages._

* Feat: add Vazirmatn font and improve layout responsiveness. 
  _- Integrated the Vazirmatn font for better typography support, especially for RTL languages.
- Enhanced layout styles to ensure better responsiveness across various screen sizes, including adjustments to margins and paddings.
- Updated various components to utilize new CSS properties for improved layout handling.
- Refactored dashboard components for better mobile usability and visual consistency._

* Feat: add POST method support for admin menu actions. 
  _Enhanced the admin menu item functionality by introducing a POST method option for system actions, allowing for confirmation prompts before executing actions. Updated the backend to support this feature and modified the translations to reflect changes in backup file paths._

* Strip spaces  in the parent panel. 

* Refactor backup and restore. 

* Refactor: update backup directory handling and improve file naming. 

* Feat: enhance child fetching and add SyncTlsStoreApi endpoint. 
  _Updated the child fetching function to include a parent API key for improved security and error handling. Increased the node timeout from 3.0 to 30.0 seconds for better performance. Added a new SyncTlsStoreApi endpoint to facilitate the import of TLS certificates into the store, with support for domain-specific syncing. Updated API decorators to enforce role-based access control for enhanced security._

* Feat: implement debug node functionality and enhance dashboard metrics. 
  _Added support for simulating multi-node panels with debug nodes, including a new `debug_node` parameter in API requests. Updated dashboard components to display panel URLs for nodes and improved chart rendering for stacked areas. Enhanced usage statistics to account for debug nodes, ensuring accurate reporting in the dashboard. Additionally, updated translations for clarity on upload and download metrics._

* Refactor: simplify version formatting in PlatformVar. 

* Feat: add domain creation template and update domain validation. 
  _Introduced a new template for domain creation and updated the domain field validation to include a filter for whitespace. The changes enhance the user interface and improve input handling for domain entries._

* Chore: update deploy path references for services/panel rename. 
  _The panel's deployment directory is being renamed from
services/hiddify-panel to services/panel; update hardcoded paths in
source, translation catalogs, and the compiled admin UI bundle to
match._

* Chore: update MANIFEST.in to prune admin_v2 directory, preventing inclusion of node_modules in the sdist and wheel. 

* Chore: update package inclusion in pyproject.toml to include all subpackages and refine exclusion patterns; enhance GitHub Actions workflow for building and publishing with improved error handling and dependency management. 

* Refactor: update DashboardView styles and JavaScript components for improved layout and functionality; enhance progress bar and toggle button implementations. 

* Feat: update UsersTrendCard component with new online user metrics and improved layout; add missing translations for online statistics. 

* Refactor: update dashboard components with improved tooltip functionality, enhance data handling for user and usage metrics, and streamline node health display. 

* Update apscheduler. 

* Optimize memory usage: replace Celery with APScheduler for background tasks, streamline app initialization, and update dependencies. 

* Feat: add DumpServerConfigs API and improve admin routing for first setup. 

* Feat: enhance dashboard components with node health metrics, improved charting, and new UI elements for better data visualization. 

* Speed up initial configs. 

* Feat: improve AdminUser and User management with enhanced UUID handling, parent admin resolution, and usage statistics validation. 

* Feat: enhance bulk registration and child ID resolution for various models, including ServerIp, TlsStore, and Proxy. 

* Feat: implement admin role validation and permission checks for creating and updating AdminUser. 

* Feat: enhance client config rendering to handle domains related to child. 

* Feat: implement legacy ENUM value remapping and enhance AdminUser timestamp updates. 

* Feat: implement last_online and last_modified_time tracking for AdminUser. 

* Feat: enhance TLS certificate handling with subject alternative names and hostname validation. 

* Fix node auth bug. 

* Feat: add DNS resolver configuration and decoy upstream snippets for HAProxy templates. 

* Temporaty fix for wiregaurd port. 

* Improve: admin list UX, override revert, and template placeholder validation. 

* Improve domain detection. 

* Fix removed column. 

* Add 3 minutes negative cache for errory config fetch. 

* Add all important domain fields. 

* Add xray array config generation, centeralized tag name. 

* Chore: tidy unused imports in database.py. 

* Make db models type safe. 

* Disable xhttp for singbox, fix domain for proxies. 

* Update api models from marshalow to pydantic. 

* Add new validation information, fix singbox configs, improve stablity. 

* Test and improve proxy supports for 80 protocols. 

* Make all protocols working fix  bugs. 

* Revert http proxy. 

* Add vless encryption, flow, insecure, http tcp none reality tcp, and much more. 

* Improve protocol compatibility. 

* Update. 

* Fix upgrade. 

* Fix upgrade issue. 

* Fix issues. 

* Update. 

* Update translation. 

* Update. 

* Update. 

* New version. 

* WIP. Add new dashboard and fully configurable backend. 

* Update. 

* Update. 

* Update. 



## v12.3.1 (2026-05-26)

#### Fix

* Issue. 



## v12.3.0 (2026-04-28)

#### New

* Add support for any domain type. 

* Add additional configs. 

* Add public ports for relay servers. 

* Add 7 days action to users, disable ip resolving in domain page, make domain page better. 

* Add dnstt. 

#### Fix

* Bug. 

* Zombie process. 

* Bug. 

* Issue. 

* Merge. 

* Issue. 

#### Other

* Merge pull request #26 from MikeKoroban/fix-wg-address. 
  _Fix missing WireGuard local interface address in sing-box subscription JSON for Hiddify clients._

* Fix WireGuard share-link generation for Hiddify app. 

* Add more dummy domains. 

* Add vaydns. 

* Update. 

* Update. 

* Update. 

* Update translations. 

* Update translations. 

* Disable ech for naive. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Update translations. 

* Update translations. 

* Merge branch 'dev' of github.com:hiddify/Hiddify-Panel into dev. 

* Update README.md. 

* Update installation link in README.md. 

* Update README.md. 

* Merge branch 'dev' of github.com:hiddify/Hiddify-Panel into dev. 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Update translations. 



## v12.0.0 (2026-02-21)

#### New

* Add accountable MTPRoxy. 

* Sperate mieru udp/tcp and customizable mieru , better naive quic support. 

* Add mieru and naive. 

#### Fix

* Password. 

* Wiregaurd and naive,ssh, mieru user usage. 

* Ech. 

* Mieru tcp. 

* H2. 

* Translation. 

* Ssh proxy. 

#### Other

* Update translations. 

* Update translations. 

* Update translations. 

* Update translations. 

* Update translations. 

* Update translations. 

* Update dependenceis, fix cloudflare api, xray json , issue in user uuid. 

* Update translations. 

* Update translations. 

* Update translations. 

* Update translations. 

* Merge pull request #21 from Alighaemi9731/feature/ech-support. 
  _feat(ech): add TLS ECH support in generated links_

* Update init_db.py. 

* Update QuickSetup.py. 

* Refactor SwitchField assignment for clarity. 

* Merge branch 'dev' into feature/ech-support. 

* Merge pull request #20 from Alighaemi9731/fix/max-active-users-zero. 
  _fix(admin): correct max active users count in admin list_

* Merge pull request #23 from Alighaemi9731/tls-fragment-packets-config-latest. 
  _feat(tls-trick): make fragment packets configurable (latest base)_

* Feat(tls-trick): make fragment packets configurable. 

* Merge branch 'dev' of github.com:hiddify/Hiddify-Panel into dev. 

* Update translations. 

* Fix(init_db): backfill ECH settings when db is already latest. 

* Fix(migration): always ensure ECH configs exist on upgraded installs. 

* Fix(ui): clean ECH setting labels in admin forms. 

* Feat(ech): add TLS ECH setting and inject ech into generated links. 

* Fix(admin): correct max active users count in admin list. 



## v11.0.17 (2026-01-25)

#### Other

* Merge branch 'tmp' into dev. 

* Update translations. 



## v11.0.16 (2026-01-25)

#### Other

* Update translations. 



## v11.0.15 (2026-01-25)

#### Other

* Update translations. 



## v11.0.14 (2026-01-24)

#### New

* Add 7 days action to users, disable ip resolving in domain page, make domain page better. 

* Add h2 support, add IP certificate, 

#### Other

* Update translation. 

* Update packages. 

* Delete 1pyproject.toml. 

* Delete a.txt. 

* Update translations. 

* Update translations. 



## v11.0.13 (2025-09-12)

#### Other

* Update translations. 



## v11.0.12 (2025-09-12)

#### New

* Add resolve IP option to domain. 

#### Fix

* * in domain name. 

#### Other

* Fix ooni issue. 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Update translations. 

* Update translations. 



## v11.0.11 (2025-07-12)

#### New

* Add actions to users. 

#### Other

* Update translations. 



## v11.0.10 (2025-07-12)

#### Other

* Disable alpn for http. 

* Add no headers in tcp stream and fix tcp settings in xray full. 

* Merge branch 'dev' of github.com:hiddify/Hiddify-Panel into dev. 

* Update translations. 



## v11.0.8 (2025-07-11)

#### Other

* Update translations. 



## v11.0.7 (2025-07-11)

#### Other

* Update translations. 



## v11.0.6 (2025-07-11)

#### Other

* Update translations. 



## v11.0.5 (2025-07-11)

#### Other

* Update translations. 



## v11.0.4 (2025-07-11)

#### Other

* Merge branch 'main' into dev. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Update translations. 

* Update translations. 

* Update translations. 

* Use dev branch for build translation. 

* Update release script. 



## v11.0.3 (2025-07-11)

#### New

* Add singbox support again, improve xray usage. 



## v11.0.1 (2025-07-10)

#### Other

* Merge branch 'main' into dev. 

* Merge pull request #19 from hiddify/beta. 
  _release_

* Update translations. 

* Merge pull request #18 from hiddify/beta. 
  _10.86.2_

* Enable tcp reality by default. 



## v11.0.0 (2025-07-10)

#### Fix

* Ssh bug. 

#### Other

* Prevent duplicate ports. 



## v10.86.3 (2025-07-10)

#### Other

* Merge branch 'dev' of github.com:hiddify/Hiddify-Panel into dev. 

* Chore: update translations with Fink 🐦 



## v10.86.2 (2025-07-10)

#### Other

* Add xray strinde ssh support. 



## v10.86.1 (2025-07-10)

#### New

* Add splithttp for old xray clients. 

#### Fix

* Change proxy settings. 

* Bug. 

* Typo. 

* Test bug. 

* Installation issues. 

* Db issue. 

* Child. 

* Db not init issue. 

* Release bug. 

* Exception showing. 

* Std out issue generation. 

* Bug. 

* Bug. 

* Webapp installation. 

* Refactor to xhttp. 

* Refactor splithttp to xhttp. 

* Upgrade issue. 

* My translation. 

#### Other

* Add resolve ip and fix cdn ip. 

* Update useragegnt. 

* Add support for reality grpc, tcp and xhttp. 

* Add translation and fix port bug. 

* Add all params to sub url. 

* New xhttp, now it is possible to have two distinct domain or alpn for download and upload, add parameters to proxies. 

* Improve auto ip selector, add random latest user_agent. 

* Disable singbox routing. 

* Update to singbox 1.11. 

* Update singbox configs. 

* Add host to tcp settings. 

* Use same date time in update. 

* Fix fragment order. 

* Speed up usage and fix concurrent bug. 

* Add reality xhttp and fix the view avaible proxies page. 

* Use global index. 

* Remove inetfaces. 

* Merge branch 'dev' into beta. 

* Update marshmallow. 

* Merge pull request #15 from tesilaaliset/fix/pin_marshmellow_version. 
  _Pining marshmellow version on uv_

* Pining marshmellow version on uv. 

* Update release script. 

* Update release script. 

* Merge pull request #12 from tesilaaliset/fix/fix_session_config_background_job. 
  _Fix using session for hiddify panel after removing flask from backgro…_

* Fix using session for hiddify panel after removing flask from background jobs. 

* Remove unused import. 

* Updte. 

* Add DISABLE_AUTO_UPDATE. 

* Improve ram and cpu usage. 

* Better logging for exceptions. 

* Convert package manager to uv. 

* Disallow background task until db upgrade is done. 

* Remove useless sqlachemy serializer. 

* Make less memory usage for background task and excluding flask in background task. 

* Reduce 70% memory usage due to inactive for most users the cloudflare api and some other enhancements. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Update translations. 

* Update translations. 

* Merge pull request #4 from ninjastrikers/main. 
  _chore: update translations with Fink 🐦_

* Merge branch 'hiddify:main' into main. 

* Update config_enum.py. 
  _adding my_

* Chore: update translations with Fink 🐦 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Update translations. 

* Update translations. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Merge pull request #10 from tesilaaliset/main. 
  _Fix error on transport key_

* Fix error on transport key. 

* Merge pull request #9 from tesilaaliset/fix/fix_poetry. 
  _Update poetry version_

* Update. 

* Merge pull request #6 from legiz-ru/mihomo. 
  _enhancements for xray, sing-box, clash configs_

* Enhancements for xray, sing-box, clash configs. 
  _clash config:
replace zh to cn for correct create config
add geoip&geosite rule-sets for ir,cn,ru with DIRECT route
GEOIP,IR & DOMAIN-SUFFIX,.ir replace to rule-sets

sing-box:
replace zh to cn for correct create config
replace .srs links to .srs from hiddify-geo
fix rule-set sing-box 1.8+ for .cn

xray config:
add geoip:ru & geosite:category-ru for DIRECT_

* Merge pull request #5 from legiz-ru/mihomo. 
  _add mihomo and fix sb_

* Add mihomo and fix sb. 
  _fix subname for sing-box app
add clash meta for android
add clash verge rev_

* Add clash icons. 
  _add clash meta for android
add clash verge rev_

* Update translations. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Update translations. 

* Update user page. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Update translations. 



## v10.80.10 (2024-12-18)

#### Other

* Update translations. 



## v10.80.9 (2024-12-18)

#### Fix

* Bug. 

#### Other

* Update translations. 



## v10.80.8 (2024-12-17)

#### New

* Optimize cli. 

#### Fix

* Upgrade for xhttp. 

#### Other

* Merge pull request #3 from ninjastrikers/main. 
  _Add Burmese to QuickSetup and Update Burmese translations_

* Added lang.my in SettingAdmin.py. 

* Adding lang.my in QuickSetup. 

* Merge branch 'hiddify:main' into main. 

* Update Burmese translation. 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Update translations. 



## v10.80.7 (2024-12-15)

#### Other

* Update translations. 



## v10.80.6 (2024-12-15)

#### Other

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Update translations. 



## v10.80.4 (2024-12-15)

#### Fix

* Telegram backup bug. 

#### Other

* Make utf8 backup. 



## v10.80.3 (2024-12-15)

#### Other

* Update app list and remove hiddifyn hiddifyng and hiddifyclash. 

* Update to singbox 1.10 template. 



## v10.80.0 (2024-12-15)

#### New

* Add wireguard and shadowsocks to supported protocols for v2rayng. 

* Add all wiregaurds to wireguard configs. 

* Add grpc. 

* Disable auto password generation. 

* Add max ip api. 

* Allow reset usage after reset days. 

* Update translations. 

* Fetch xray configs if use xray backend in hiddify next is enabled. 

* Make dotenv loads from app.cfg. 

* Add password auth in REDIS_URI. 

* Add local host keys in sub link. 

* Set ssh host keys from configs to be able to make backup. 

* Add password for admins. 

#### Changes

* Update dependencies. 

#### Fix

* Version. 

* Resolve bug. 

* Translation issue. 

* Bug when a key is not needed. 

* Fake domain bug. 

* Typo. 

* Excpetion. 

* Translations. 

* Domain bugs. 

* Bug. 

* Ipv6 in quick setup. 

* Ipv6 check in quick setup. 

* Cloudflare bug. 

* Bug. 

* Backup to telegram issue. 

* Exception view in api. 

* Csrf issue in proxy. 

* Missed package. 

* Mysqlclient. 

* Cache iisue. 

#### Other

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Update translations. 

* Update translations. 

* Update. 

* Update translations. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Merge pull request #1 from legiz-ru/ru_extended. 
  _Add Russia to QuickSetup_

* Add Russia to QuickSetup. 

* Better presentation of wireguard configs. 

* Never remove json translation. 

* Rename splithttp to xhttp. 

* Better manage users. 

* Improve. 

* Update domain handler. 

* Refactor domain checker. 

* Improve some codes. 

* Improve tg bot exception handling. 

* Optimize active users. 

* Remove. 

* Remove bug. 

* Refactor the code and add modules dynamicatonally for future extensions. 

* Create app. 

* Update translations. 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Update translations. 

* Update translations. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Update translations. 

* Check. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Update translations. 

* Update. 

* Update translations. 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Update dependencies. 

* Update cloudflare api. 

* Update. 

* Remove unused packages. 

* Update translations. 

* Add reset owner password cli. 

* Enabling CSRF for Panel. 

* Switching to poetry. 

* Save ssh host keys in the databse. 

* Merge pull request #224 from legiz-ru/updateapplinks. 
  _add hiddify ios client(Update apps_api.py)_

* Add hiddify ios client(Update apps_api.py) 

* Merge pull request #223 from legiz-ru/updateapplinks. 
  _Add sing-box graphic client + fix v2rayng github url (Update apps_api_.py)_

* Fix MacOS singbox DMG download apps_api.py. 

* Change sorting app list apps_api.py. 

* Fix direct macos dmg sing-box apps_api.py. 

* Fix direct github download sing-box android apps_api.py. 

* Fix direct android apk sing-box apps_api.py. 

* Fix v2rayng and sing-box android direct link. 
  _Update apps_api.py_

* Apps_api.py correct apps_data += 

* Merge pull request #1 from legiz-ru/updateapplinks2. 
  _add sing-box apps_api_

* Add sing-box apps_api. 

* Add sing-box (en lang) 

* Add sing-box (pt lang) 

* Add sing-box (fa lang) 

* Add sing-box (ru lang) 

* Add sing-box. 

* Add sing-box. 

* Add singbox ico. 

* Merge pull request #221 from ninjastrikers/main. 
  _Adding Burmese (my) translations_

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Merge pull request #222 from legiz-ru/main. 
  _Fix for RU sing-box config [Update base_singbox_config.json.j2]_

* Update base_singbox_config.json.j2. 
  _fixing sing-box json for bypass geosite-ru geoip-ru https://github.com/hiddify/Hiddify-Manager/issues/4545_

* Update translations. 



## v10.70.7 (2024-08-19)

#### Other

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Update translations. 



## v10.70.6 (2024-08-17)

#### Fix

* Telegram bot backup. 



## v10.70.5 (2024-08-15)

#### Fix

* Telegram exception. 

#### Other

* Make null configs no ping. 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Update translations. 



## v10.70.4 (2024-08-02)

#### Fix

* Bug. 

#### Other

* Update translations. 



## v10.70.3 (2024-08-02)

#### Fix

* Daily usage. 

* Qrcode not fit to modal. 

#### Other

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Chore: update translations with Fink 🐦 

* Merge pull request #219 from XopoIII/main. 
  _Update translations_

* Merge branch 'main' into main. 

* Merge pull request #220 from jxo-me/main. 
  _Update qrcode.js Fix QR code style overflow_

* Merge branch 'hiddify:main' into main. 

* Update qrcode.js Fix QR code style overflow. 
  _Fix QR code style overflow_

* Merge branch 'main' into main. 

* Chore: update translations with Fink 🐦 

* Update translations. 



## v10.70.2 (2024-07-30)

#### Fix

* Buggy update. 

#### Other

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Update translations. 



## v10.70.1 (2024-07-30)

#### Other

* Add more logs to usage update. 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Add generate_204. 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Update translations. 



## v10.70.0 (2024-07-29)

#### New

* Add  url test. 

* Add xray fragment. 

* Add h3 for splithttp. 

* Add html editor for user custom text. 

* Add wiregaurd output for wireguard application. 

* Add splithttp. 

* Add lock in updating usage. 

* Add try catch in get user usage. 

#### Changes

* Add alpn to path. 

* Work splithttp in hiddify. 

#### Fix

* Clash link. 

* Shadowtls. 

* Shadowsocks bug. 

* Quic bug in sub link. 

* Xray bug. 

* Quic. 

* Bug???? 

* Api patch bug. 

* Bot issue. 

* Permission issue. 

* Incorrect ssh warning. 

* Reality issue. 

* Bug. 

* Incorrect  usage. 

* Bug in adding fake domain. 

#### Other

* Wireguard tuic and hysteria added to clashmeta link. 

* Update translations. 

* Remove wireguard noise. 

* Update translations. 

* Update translations. 

* Remove fragment in for quic. 

* Update translations. 

* Update translations. 

* Update translations. 

* Update translations. 

* Chore: update translations with Fink 🐦 

* Update translations. 

* Change useragent of splithttp. 

* Add more tags for free text. 

* Update translations. 

* Chore: update translations with Fink 🐦 

* Update translations. 

* Update translations. 

* Better reinstall or apply policy. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Update translations. 

* Reduce overhead. 

* Reduce overhead. 

* Force:60 seconds lock. 

* Disable splithttp by default. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Update translations. 



## v10.50.4 (2024-07-17)

#### Fix

* Small bugs. 

#### Other

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Update translations. 



## v10.50.3 (2024-07-14)

#### Other

* Update translations. 



## v10.50.2 (2024-07-14)

#### Fix

* Reality bug. 

* Ignoring fake domain for no domain proxies. 

#### Other

* Update translations. 



## v10.50.1 (2024-07-14)

#### Other

* Update translations. 



## v10.50.0 (2024-07-14)

#### New

* Better ipv6 and ipv4 managemnt. 

* Add quick setup steps and disable some services by default. 

* Add more system api such as update usage and all configs. 

#### Changes

* Update api to v3. 

* Better ui for start and end date. 

#### Fix

* Xray in json config. 

* Reset cache bug. 

* Invalidate cache after changing settings. 

* Sorting issue. 

* Api uuid bug. 

* Translation bug. 

* Bug in v2ray. 

* Bugs in update usage. 

* Sorting bug. 

* Xray sub order. 

#### Other

* Update translations. 

* Update translations. 

* Allow fake domain to be empty. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Allow host to be empty. 

* Update translations. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Update translations. 

* Update. 

* Update translations. 

* Update_translation. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Update translations. 

* Add id in user. 

* Update translations. 

* Temporary remove active devices. 

* Optimize update xray  usage. 

* Optimize update wireguard  usage. 

* Optimize update ssh usage. 

* Update translations. 

* Chore: update translations with Fink 🐦 

* Update translations. 

* Fix bug. 

* Update translations. 



## v10.30.6 (2024-07-06)

#### Changes

* Default  of reset usage and reset days are not false. 

#### Other

* Update translations. 



## v10.30.4 (2024-07-02)

#### Other

* Update translations. 



## v10.30.2 (2024-07-02)

#### Other

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Update translations. 



## v10.30.0 (2024-07-02)

#### New

* Add reset proxies. 

* Optimize priodic reset usage. 

#### Changes

* Better logging. 

* Fix red lines for hconfig. 

* Fix & refactor cloudflare api codes. 

* Reduce complexity for reality domain validation. 

* Fix possible bug. 

* Improve sync child with parent operation. 

* Refactor logger. 

* Sync node in background. 

* Refactor version checking. 

* Vmess "security" field to auto instead of chacha20-poly1305. 

* Enable hysteria2 on old_xtls_direct domain. 

* Refactor Domain model. 

* Hide sub enable/disable toggle(except xray json) 

* Send configs even if the sub is disabled. 

* Refactor. 

#### Fix

* Bug. 

* Lang change in admin. 

* Custom type. 

* Resetting user's usage value in update usage operation. 

* Typo. 

* The shadowsocks2022 config in V2rayng, Streisand, Shadowrocket (the link sub) the other shadowsocks related configs like shadowtls, ssfaketls should be fixed. 

* The shadowsocks2022 config in V2rayng (xray sub) 

* Last_version not defined. 

* Enabling/disabling ssfaketls. 

* Cloudflare api bug related to root/sub domains. 

* ASN checking. 

* Default warp mode. 

* Not installing warp. 

* Child's user/admin links bug. 

* Parent panel links bug. 

* Bug. 

* Outside app context bug. 

* Wireguard usage api bug. 

* Bugs related to venv. 

* Venv bug. 

* Bug & refactor. 

* Telegram bot registering bug. 

* Incorrect condition when current_usage_GB is 0 bug. 

* User api endpoints. 

* Admin api endpoints. 

* Hiddifycli_enable key not found bug. 

* Send xray sub if client supports. 

* Mux in xray sub. 

* Sub bug. 

#### Other

* Update. 

* Update translations. 

* Remove enable keyword in translations. 

* Update translations. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Explicitly remove expiry date. 

* Fix. 

* Merge pull request #214 from Iam54r1n4/devp10-patch-21. 
  _Fix resetting user's usage value in update usage_

* Update usage.py. 

* Update user.py. 

* Merge pull request #216 from Iam54r1n4/devp10-patch-23. 
  _Fix the shadowsocks2022 bug in V2rayng, Streisand, Shadowrocket clients_

* Update xray.py. 

* Merge pull request #213 from Iam54r1n4/devp10-patch-20. 
  _Fix cloudflare API section_

* Merge pull request #212 from Iam54r1n4/devp10-patch-19. 
  _Fix adding reality domain_

* Merge pull request #217 from glory7sa/main. 
  _Update translations RU_

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Merge pull request #215 from Iam54r1n4/devp10-patch-22. 
  _Fix warp installation & Disable telegram mtproto by default_

* Merge pull request #211 from Iam54r1n4/devp10-patch-18. 
  _Improve api security_

* Improve: api security fixed admin privilege esclation. 

* Merge pull request #210 from Iam54r1n4/devp10-patch-17. 
  _Improve security_

* Improve: security Thanks to N1k4, an XSS vulnerability was detected, this commit fixes it Note: the bleach library is deprecated but i think it's still the best choice. 

* Merge pull request #209 from Iam54r1n4/devp10-patch-15. 
  _Run sync child with parent operation in seperate thread & Improve sync api_

* Del: initiate logger log. 

* Merge pull request #208 from Iam54r1n4/devp10-patch-16. 
  _Fix version checking_

* Add: todo. 

* Merge pull request #206 from Iam54r1n4/backward-hysteria-tuic_old_direct_domain. 
  _Update domain.py_

* Update domain.py. 

* Merge pull request #207 from Iam54r1n4/devp10-patch-14. 
  _Fix wireguard usage api bug_

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Chore: update translations with Fink 🐦 

* Update translations. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Merge pull request #201 from Iam54r1n4/devp10-patch-10. 
  _Fix venv bug panel side_

* Merge pull request #202 from Iam54r1n4/devp10-patch-11. 
  _Change vmess "security" field to auto instead of chacha20-poly1305_

* Merge pull request #203 from Iam54r1n4/devp10-patch-12. 
  _Change enable hysteria2 on old_xtls_direct domain_

* Merge pull request #204 from Iam54r1n4/patch-1. 
  _Update user.py (API bug)_

* Update user.py. 

* Merge pull request #205 from Iam54r1n4/devp10-patch-13. 
  _Refactor Domain model_

* Merge pull request #199 from Iam54r1n4/devp10-patch-8. 
  _Change sending sub_

* Merge pull request #198 from Iam54r1n4/fix-usages-color. 
  _Fix usages color_

* Better darkmode view. 

* Fix usages color. 

* Merge pull request #200 from Iam54r1n4/devp10-patch-9. 
  _Fix api bug_

* Add: fetching telegram bot info command to hiddifypanel cli. 

* Merge pull request #197 from Iam54r1n4/devp10-patch-7. 
  _Fix & Refactor APIs_

* Merge pull request #196 from Iam54r1n4/devp10-patch-6. 
  _Add enable/disable(ing) specific subscriptions feature_

* Add: enable/disable(ing) specific subscriptions. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 



## v10.20.3 (2024-04-12)

#### Fix

* Another warp_sites bug. 

#### Other

* Merge pull request #195 from Iam54r1n4/devp10-patch-5. 
  _Add usage to xray sub & code refactor_

* Add: usage to xray sub & code refactor. 

* Merge pull request #194 from Iam54r1n4/devp10-patch-4. 
  _Fix another warp_sites bug_

* Update translations. 



## v10.20.2 (2024-04-12)

#### Fix

* Warp_sites validation. 

#### Other

* Merge pull request #193 from Iam54r1n4/devp10-patch-4. 
  _Fix warp_sites validation_



## v10.20.1 (2024-04-12)

#### Other

* Update translations. 

* Update. 



## v10.20.0 (2024-04-12)

#### New

* Add warp_sites validator. 

* Add remaining days to reset. 

#### Changes

* Auth. 

* Remove uuid as apikey (except for register) 

* Better redis cache invalidation. 

* Seperate child and node. 

* Don't login with super admin account in node api calls need to be tested. 

* Use Child.current instead of g.node in node apis need to be tested. 

* Log to stdout. 

* Refactor api_client(test) 

* Refactor. 

* User model ips property to devices. 

* Improve code. 

* Refactor api structure & implement get_panel_info function. 

* Better query. 

* Refactor child.py. 

* Node auth. 

* Child-parent(node) auth. 

* Parse parent_panel as it's parent url with uuid (no unique id) 

* Refactor. 

* Refactor & bug fix. 

* Hide parent settings for now. 

* Refactor. 

* Hide parent setting when panel is in parent mode. 

* Refactor. 

* Refactor. 

* Refactor & bug fix. 

* Authentication approach in api calls between child and parent. 

* Little refactor. 

* Improve usage api approach. 

* Enable sync with parent when needed. 

* Refactor child aliveness api. 

* Send parent api request with api key. 

* Parent APIs route (remove UUID) 

* Refactor. 

* Cleanup. 

* Refactor & bug fix - child-parent-api. 

* Don't set child_unique_id field manually in apis(there's no need anhymore) little refactoring. 

* Change panel self child(child with 0 id) unique_id to hconfig(ConfigEnum.unique_id) instead of default "self" value. 

* ConfigEnum.parent_panel category to too_advanced. 

#### Fix

* Get only enabled proxies for subs. 

* Show tuic enable & port options in sttings. 

* Show hysteria enable option. 

* Flash bug when enable/disable ing proxies. 

* Don't send unsupported protocols in v2rayng sub. 

* Typo. 

* Shadowsocks config & update usage bug. 

* Xray update usage bugs. 

* Icon. 

* Markup session bug, disallow duplicate domain. 

* Bug in adding new enum. 

* Proxy status byg. 

* Bug. 

* Child bug. 

* Sqlachemey update. 

* Send backup to admin through telegram bot. 

* Add admin bug. 

* Issue. 

* Empty sites. 

* Get proxies. 

* Bug. 

* Bug. 

* Bug. 

* Node auth. 

* Redis_cache again. 

* Redis_cache bug. 

* Usage. 

* Bug. 

* Bug. 

* Bug. 

* Bug in usage api. 

* Bug. 

* Bugs. 

* Circular import. 

* Bug. 

* Missing import. 

* Missing import. 

* Status api bug. 

* Bug. 

* Circular dependency. 

* Refator. 

* Merge conflict. 

* Bug. 

* Users usage api bug. 

* Sync request bug. 

* Bug in register api. 

* Adding parent. 

* Status api bug. 

* Flask error handler. 

* Bug. 

* Bug in hiddify_api & init child APIs to app. 

* Bug in hiddify_api. 

* Bug in authentication. 

* Small bug. 

* Register/sync. 

* Parent admin links in admin layout sidebar. 

* Sync usage with parent automatically. 

* Usage api (child side) 

* Usage api (in child) 

* Usage api. 

* Child parent usage api. 

* Bug. 

* Usage api (test) 

* Bug in getting child status. 

* Parent dashboard bug. 

* Adding domain bug. 

* Admin layout ui (parent mode) 

* Bugs. 

* Bug. 

* Bug. 

* Bug and add description. 

#### Other

* Merge pull request #192 from Iam54r1n4/devp10-patch-3. 
  _Handle v2rayng sub & bug fix_

* Add: add xray json configs to auto sub options. 

* Refactor. 

* Fix bug? 

* Update. 

* Update translations. 

* Revert SerializerMixin. 

* Merge pull request #191 from Iam54r1n4/devp10-patch-2. 
  _Fix shadowsocks bug_

* Add: xray subscription to UI. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Update translations. 

* Update translations. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Update translations. 

* Fix bug of init db printing not stderr. 

* Update translations. 

* Update. 

* Merge pull request #189 from Iscgr/main. 
  _Update translations_

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Merge branch 'hiddify:main' into main. 

* Fink 🐦: update translations. 

* Merge pull request #190 from Iam54r1n4/devp10-patch-1. 
  _Bug fix_

* Update. 

* Fink 🐦: update translations. 

* Update. 

* Update to python 3.13. 

* Update. 

* Update. 

* Update dependencies. 

* Update translations. 

* Merge. 

* Merge pull request #187 from Iam54r1n4/devp-child-parent. 
  _Implement child-parent(Nodes) API (Partly)_

* Update config.py. 

* Update child.py. 

* Update api_client.py. 

* Update api_client.py. 

* Update base.py. 

* Merge branch 'main' into devp-child-parent. 

* Merge pull request #188 from Iam54r1n4/devp-disable-config. 
  _disable unwanted configs_

* Add: quic/xtls/h2"_enable" configs. 

* Add: tcp enable. 

* Add: vless/trojan/reality"_enable" configs. 

* Merge pull request #183 from NiklasBuchfink/main. 
  _Add Ninja i18n lint action_

* Rename ninja-i18n.yml to ninja_i18n.yml. 

* Add ninja-i18n.yml. 

* Chg. 

* Del: parent_admin_uuid config. 

* Chg. 

* Add: string/bool field to hconfig schema. 

* Chg. 

* Add: enum type descr to config_enum.py. 

* Add: logging to child/parent apis. 

* Add: invalidate cache after sync/register. 

* Add: invalidate_all_cached_functions to redis cache. 

* Add: logging to project and use it in hutils.node. 

* Chg. 

* Add: api http client & refactor api schemas. 

* Add: version checking before registering. 

* Add: panel info api (for now just getting panel version) 

* Add: log level config. 

* Add: new parent as a chlid to child parent after registering chg: node auth. 

* Chg. 

* Del: if. 

* Better: query. 

* Del: extras. 

* Del: set_db parameter. 

* Update xray_api.py. 

* Add: db version for parent configs. 

* Merge branch 'devp-child-parent' of github.com:Iam54r1n4/HiddifyPanel into devp-child-parent. 

* Add: send sync request to childs from parent when needed. 

* Add: request child to sync to hiddify_api.py. 

* Add: sync with parent api for child. 

* Add: child status api for parent. 

* Add: request to register (child side) 

* Add: some apis to child panel named actions these apis allow the parent panel to control the child panel. 

* Add: register parent api used in parent panel to tell a panel register itself with the parent panel, if this api return 200 status code, means the targeted panel registered in parent. 

* Add: authenticate request with panel unique id itself used in child-parent api calls. 

* Add: panel_mode to str_config. 

* Del: old unwanted code. 

* Del: commented commands. 

* Add: set db from parent api response. 

* Add: parent api key. 

* Add: equalize panel unique id and root child unique id. 

* Add: insert data. 

* Del: unused. 

* Merge branch 'hiddify:main' into child_parent_api. 

* Merge branch 'hiddify:main' into child_parent_api. 

* Chg. 

* Merge branch 'child_parent_api' of github.com:Iam54r1n4/HiddifyPanel into child_parent_api. 

* Use: child-parent apis. 

* Merge branch 'child_parent_api' of github.com:Iam54r1n4/HiddifyPanel into child_parent_api. 

* Del: child's apis blueprint (we don't need them as an public api) 

* Move child's apis to hiddify_api.py file. 

* Merge branch 'main' of github.com:hiddify/HiddifyPanel into child_parent_api. 

* Add: to_schmea and from_schema methods to models add: some function to utils. 

* Add: usage api. 

* Add: sync api. 

* Add: register api. 

* Del: unnecessary imports. 

* Add: description to api schemas. 

* Refactor: admin APIs. 

* Refactor: user APIs. 



## v10.14.0 (2024-03-25)

#### Fix

* Backup issue. 

* Bug. 

* Bug. 

* Bug of inactive drivers. 

#### Other

* Add secret. 

* Disable usage for xray when only singbox. 

* Update. 

* Update ui. 

* Optimize user usage. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Add version to title. 

* Update translations. 



## v10.12.1 (2024-03-20)

#### Fix

* Wireguard update usage bug. 

#### Other

* Merge pull request #185 from Iam54r1n4/devp-patch1. 
  _Fix Wireguard update usage bug_

* Merge pull request #184 from Sovamm/main. 
  _Update translations_

* Fink 🐦: update translations. 



## v10.12.0 (2024-03-19)

#### New

* Add norooz. 

#### Changes

* Hiddify next download urls. 

#### Fix

* Reality ASN checking bug. 

* Tcp brutal. 

* Bug. 

* Proxy status. 

#### Other

* Merge pull request #140 from Iam54r1n4/dev-patch21. 
  _Change hiddify client(next) download urls_

* Merge pull request #179 from MRDOCTOROO/main. 
  _Update translations_

* Fink 🐦: update translations. 

* Merge branch 'hiddify:main' into main. 

* Fink 🐦: update translations. 

* Merge pull request #180 from Iam54r1n4/dev-patch49. 
  _Fix reality ASN checking bug_

* Merge pull request #181 from pjrobertson/macos_link. 
  _Fix 2nd link to mac os download_

* Fix up all URLs for hiddify clash desktop. 
  _See the actual URLs in https://github.com/hiddify/HiddifyClashDesktop/releases - it contains 'v' before the first version number_

* Fix 2nd link to mac os download. 
  _Really fixes #3820 - also makes the code DRY so as to improve maintainability_

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Better auth. 

* Merge pull request #178 from Iam54r1n4/dev-patch48. 
  _Fix sub bug_

* Some refactor for multi node. 

* Update translations. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Merge pull request #175 from Iam54r1n4/dev-patch46. 
  _Add mixed case domains in client configs_

* Add: mixed case domains in client configs all client don't support mixed case feature internally. 

* Merge pull request #176 from Arbelin94/main. 
  _Update translations_

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Merge pull request #177 from Iam54r1n4/dev-patch47. 
  _Add sending telegram msg to selected users_

* Update user_list.html. 

* Add: sending telegram msg to selected users. 

* Disable redirect for clients. 



## v10.11.1 (2024-03-16)

#### Changes

* Fix bug & refactor. 

* Refactor singbox.py. 

* Complete/improve code. 

#### Other

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Update translations. 

* Remove orig mtproxy, make erlang as defult. 

* Merge pull request #170 from Iam54r1n4/dev-patch43. 
  _Add xray configs_

* Add: xray configs. 



## v10.11.0 (2024-03-15)

#### New

* Auto update translations. 

#### Changes

* Generate essential fields before insert model automatically. 

* Even more refactor. 

* Nice refactor. 

* Refactor. 

* Yet refactoring. 

* More refactoring. 

* Refactor link_maker. 

* Refactor. 

* Refactor. 

* Import. 

#### Fix

* Reality fields. 

* Send httpupgrade proxies to streisand client. 

* Ssh link. 

* Mux parameters in subscription link (v2ray/xray format) according to ray2sing. 

* Subscription links bug. 

* Circular imports. 

* Update-wg-usage bug. 

* Vless|trojan header type bug. 

#### Other

* Merge pull request #174 from er888kh/main. 
  _Update base_singbox_config.json.j2_

* Update base_singbox_config.json.j2. 
  _Correctly bypass geoip and geosite download url.

The default bypass list only includes `githubusercontent.com` but it should also contain `raw.githubusercontent.com`. Note that this problem only manifests in clients which have just recently installed singbox. For those who already had singbox with a working hiddify installation, they already have the cache files and the file updates flawlessly._

* Fink 🐦: update translations. 

* Update translations. 

* Update Translation. 

* Merge pull request #173 from pjrobertson/macos_link. 
  _Fix download link for macos hiddify clash link._

* Fix download link for macos hiddify clash link. Fixes #3820. 

* Merge pull request #172 from Iam54r1n4/dev-patch45. 
  _Fix REALITY fields_

* Fstring is not recognizable. 

* Chg. 

* Chg. 

* Chg. 

* Merge pull request #171 from Iam54r1n4/dev-patch44. 

* Merge pull request #169 from Iam54r1n4/dev-patch41. 
  _Refactor link maker_

* Merge branch 'dev-patch41' of github.com:Iam54r1n4/HiddifyPanel into dev-patch41. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Merge pull request #165 from Iam54r1n4/dev-patch39. 
  _Fix resend httpupgrade proxies to streisand client again_

* Merge pull request #166 from Iam54r1n4/dev-patch40. 
  _Fix 'pp' parameter from ssh link_

* Update link_maker.py. 

* Del: 'pp' parameter from ssh link. 

* Merge pull request #168 from Iam54r1n4/dev-patch42. 
  _Fix mux(multiplex) parameters in subscription link (v2ray/xray format) according_

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Enable cdn ip check. 

* Nonesense. 

* Merge pull request #162 from Iam54r1n4/dev-patch36. 
  _Fix subscription links bug_

* Improve: condition. 

* Merge pull request #163 from Iam54r1n4/dev-patch37. 
  _Add proxy stats button & Fix bug_

* Add: proxy stats button. 

* Merge pull request #164 from Iam54r1n4/dev-patch38. 
  _Fix circular imports_

* Merge pull request #161 from Iam54r1n4/dev-patch34. 
  _Fix user usage bug & Refactor_

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 

* Fink 🐦: update translations. 



## v10.10.20 (2024-03-11)

#### Other

* Enable http upgrade by default. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 



## v10.10.19 (2024-03-10)

#### Other

* Update user front. 



## v10.10.18 (2024-03-10)

#### Changes

* Config.py. 

* Order of sub links. 

#### Fix

* Reality bug. 

* Silly bug. 

* Restart system bug. 

* Ssh proxy link for shadowrocket & streisand clients. 

* Bug in get debug ip. 

#### Other

* Some ui improvement. 

* Merge pull request #158 from Iam54r1n4/dev-patch31. 
  _Fix reality proxy bug_

* Merge pull request #156 from Iam54r1n4/dev-patch28. 
  _Fix debug ip bug_

* Merge pull request #153 from Iam54r1n4/dev-patch28. 
  _Bug fix_

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 



## v10.10.17 (2024-03-07)

#### Other

* Fix issu in mysqlclient. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Inlang: update translations. 

* Set header type for tcp. 



## v10.10.16 (2024-03-07)

#### New

* Allow change l3 in the proxy list. 

#### Other

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 



## v10.10.15 (2024-03-07)

#### Other

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 



## v10.10.14 (2024-03-07)

#### Fix

* Incompatible types. 

* Buggy database. 

* Bug. 

#### Other

* Force add adimn user. 



## v10.10.13 (2024-03-07)

#### Fix

* Some bugs. 



## v10.10.10 (2024-03-07)

#### New

* Fix translation. 

* Add inlang translation. 

* Add more security for first login. 

* Refactor usage driver. 

* Add mass disable/enable to proxies. 

* Add support for httpupgrade. 

* Add switch for enable/disable ws, grpc, httpupgrade globally. 

* Add shadowsocks2022 support. 

* Add faketls with 2022 shadowsocks model. 

* Add search to proxy details. 

* Show progress details and hide log window. 

* Use fast_enum fix: bugs and refactor. 

* Optimize panel. 

* Add initial virtual child support. 

* Add wireguard. 

* Add indivisual config for relay. 

* Refactor configenum. 

* Customizable message added. 

* Add share link in user admin with qrcode. 

* Handle singbox v1.8 and v1.7. 

* Add insert secret code. 

* Add full backward compatiblity. 

* Add login page. 

* Use slugify. 

* Base class for admin and user models. 

* Check permission for AdminUserApi. 

* Check permission for AdminUsersApi. 

* Account atuhentication approach. 

* Implement custom flask-login for - seperate storing account id in session. 

* Handle new proxy paths (test) 

* Add login_required to user's apis. 

* Redirect old apis url to new url. 

* Use log api for getting logs. 

* JS to get logs files in result.html. 

* Auth.login_required (supports roles) 

* Better handling user change. 

* Add stars. 

* Better exception handling. 

* Add license to api. 

* Add user v2 API. 

* Add link to api. 

* Add api v2. 

* Fix quick stup stuck after restore backup. 

* Add last version of release and beta in make. 

* Add admin path to config. 

* Add admin links. 

* Hide incorrect mode proxies. 

* Filter the payment and big companies to avoid phishing detection in decoy site. 

* Add warp custom sites. 

* Add issue from menu. 

* Add custom CFG path. 

* Fix bug when no backup exist. 

* Add russian lang. 

* Add Russian translation. 

* Add reality port cli. 

* Better usage icon. 

* Add fake domains also. 

* Add hystria and tuic. 

* Add beta pre-release. 

#### Changes

* Don't send httpupgrade proxy to Streisand. 

* Fix format of jinja commands. 

* Refactor code with autopep8. 

* Useragent cache version. 

* Send mux_max_stream in mux parameter. 

* Refactor code. 

* Refactor view logs action. 

* Refactor user. 

* Refactor. 

* Refactor. 

* Show add telegram bot pop up. 

* Bool configs only return bool and others return str. update translations. 

* Refactor. 

* Don't send fragmentation to hiddify-next. 

* Override root admin is disabled by default. 

* Remove unused argument/parameter. 

* Send args in link (asn,mode...) 

* Seperate clash and clashmeta endpoints. 

* All-configs api links. 

* Update configs link. 

* Refactor getting lang. 

* Hide telegram id in add/edit page. 

* Hide histeria port from setting ui. 

* Hysteria link makeri (client link) 

* NOTHING IMPORTANT. 

* Make sessions permanent for two days. 

* Allow backward compatibility. 

* Refactor proxy model. 

* Refactor DailyUsage model. 

* Refactor. 

* Revert links to old format. 

* Update ui. 

* Add full backward compatiblity. 

* Add common_bp. 

* Refactor parent domain model. 

* Refactor DailyUsage. 

* Add backward compatibility. 

* Refactor admin and user model. 

* Refactor. 

* Refactor. 

* Fix role management. 

* Refactor. 

* Hidden old proxy path. 

* Remove duplicate password check. 

* Remove filter_by. 

* Refactor. 

* Admin login links. 

* Api v1 blueprint name. 

* Refactor. 

* APIs links to new format. 

* Refactor. 

* Authenticate user panel endponit with Authorization header even there is cookie. 

* Using server_status log api. 

* Send api calls with cookie instead of ApiKey. 

* Better readability. 

* Basic athentication realm value. 

* Better names. 

* Apiflask authentication to auth_back.py file & remove unused imports. 

* Backward compatibility. 

* Init. 

* New route page. 

* Rename. 

* Remove <user_secret> from routing in blueprint. 

* Authentication. 

* If client sent user/pass we try to authenticate with the user/pass, THEN we check session cookies. 

* Use hiddify-manager/common/commander.py instead of running the scripts directly. 

* Version parameter type to int in ip.py functions fix: typo and bugs. 

* Make ip_utils a package. 

* Get ip approach & validation in DomainAdmin.py. 

* Show xui_importer error if occurred. 

* Short api. 

* Ui files. 

* Use apiflask abort. 

* Change AdminDTO to AdminSchema. 

* Better naming. 

* Reorganize domain ports. 

* Update hysteria2 link. 

* Update hiddify next download link. 

#### Fix

* Fragment issue. 

* Bug. 

* Bug in checking is telegram proxy enable process. 

* Changing telegram proxy program. 

* Bug. 

* Fragment bug. 

* Exception when there is no valid domain. 

* Don't let user create invalid domains. 

* Unrequired fields in api (patch method) 

* Domain bug. 

* Bug. 

* Incorrect type ip addr. 

* Ssh server. 

* Release message. 

* Custom usage trojan. 

* Setting telegram web hook. 

* Bug. 

* Csrf check. 

* Shadowsocks bug. 

* Translation issues. 

* Inlang. 

* Jinja char prefix. 

* Update usage bug. 

* Bug. 

* Bug & refactor. 

* Hiddifynext 14 version configs fields. 

* Add user api (current_usage_GB field) 

* Bug took 3 hours. 

* Bug. 

* Url encode space seperated user names. 

* Change decoy_domain in first/quick setup page. 

* Bug. 

* Bug. 

* Dependency issue. 

* Show force cdn ip. 

* Vless trojan protocol headerType parameter in streisand. 

* Mux to be compatible with streisand|shadowrocket clients & fix fragment in shadowrocket. 

* Is telegram_enable field in api. 

* Admin log. 

* Admin api bug. 

* Bug. 

* Backup bug. 

* Develop backup bug. 

* Backup resources bug. 

* Bugs. 

* Bug. 

* Bug. 

* Bug. 

* Bug. 

* Bug. 

* Bug. 

* Fragemnt. 

* Wireguard key generation. 

* Bug. 

* Disable redirect on import config. 

* Bug when usage iis null. 

* Import bug. 

* Ui. 

* Not showing reality and fake domains. 

* No success pop up. 

* Singbox fg parameter sending. 

* Backup restore bug. 

* Some config related issues. 

* Referrer only for same origin. 

* Bug when new domain changed. 

* Api key bug. 

* Anonymous account bug. 

* Ua bug. 

* Update translation. 

* Fragmentation & mux. 

* Mtproxies link. 

* Bug. 

* Backup & auto ip selector bug. 

* Bug. 

* Show sub link as profile url. 

* Wireguard link. 

* Bug in downloading backup. 

* Show log in status page by default. 

* Getting log file & refactor. 

* Silly db bug. 

* Proxies bug. 

* Bugs/typos. 

* Permission. 

* Send telegram message. 

* Bugss. 

* Child bug. 

* Bugs. 

* Bug. 

* Req. 

* Bug. 

* Bug. 

* Mtproxies api. 

* Mtprotoproxy library link. 

* Xray fg. 

* Fragmentation for other clients except hiddify-next. 

* Get app icon url bug. 

* Typo. 

* Bug in wireguard. 

* Bug. 

* Bug. 

* Bugs. 

* Bug. 

* Translation bug in babel. 

* Bug. 

* Bug. 

* Telegram sending msg bug & babel. 

* Telegram_id bug. 

* Bug in domain. 

* Telegram id. 

* Better comment. 

* Report not defined bug. 

* Typo. 

* Send tls tricks only if proxy is cdn and client supports. 

* Bug chg: refactor. 

* Showing default mux_protocol in ui. 

* Bug. 

* Import bug. 

* Typo. 

* Bug. 

* Bug. 

* Bug in user id. 

* Auth bug. 

* Exception in account. 

* Locale bug. 

* Agent admin permission. 

* User panel lang. 

* Send message to admin's users itself. not to other admins. 

* Telegram id active representationo add: telegram id field to user edit/add page. 

* Send message to user in telegram. 

* Bug. 

* Useragent echo. 

* Singbox 1.8. 

* Redis url. 

* Bug in release. 

* Bug for hiddify next. 

* Hysteria2 bug. 

* Bug in singbox. 

* Bug. 

* Typo. 

* Don't show progress bar for update usage too. 

* Bug in getting configs. 

* Don't show progress bar for restart/reset too. 

* Don't show progress bar in /status/ 

* Progress bar. 

* Lang. 

* Bug. 

* Bug. 

* Bug. 

* Bug in fill_username. 

* Empty admin message. 

* Compatibility issue with old version. 

* Bug. 

* Bug. 

* Bug in singbox 1.7. 

* Hiddify client version. 

* Bug. 

* Admin link bug. 

* Bug. 

* Bug in singbox config. 

* Limited length of username and password. 

* Issue in updating ua. 

* Fix: login by uuid@domain.com. 

* Bug. 

* All config bugs. 

* Singbox. 

* Deep link url. 

* Auth. 

* Typo. 

* Typo. 

* Typo. 

* Json serializer bug. 

* Bug in useragent. 

* Remove print. 

* Remove prints. 

* Bugs, refactor changes, remove unneccessary dependency to flask_login. 

* Bug. 

* Bug. 

* Bug. 

* Backward compatiblity. 

* Bug. 

* Bug. 

* Bugs. 

* Bugs. 

* Backward compatibility issues. 

* Bugs. 

* Telegram get_usage_data user link. 

* Admin/user APIs (validation,parenting,recursive fetching) 

* Bugs and add login blue print. 

* Static path. 

* Bugs. 

* User bug. 

* Proxy path validation. 

* Admin me api. 

* Bug. 

* Bug in QuickSetup. 

* Auto removing UUIDs from api requests. 

* Short api again. 

* Short api. 

* Api v1 routing. 

* Remove user/pass from short api link. 

* Api v1 telegram endpoints. 

* Backward compatibility. 

* Bug. 

* Typo in redirect.html file. 

* Add just proxy_path_admin and proxy_path_client. 

* Disable CORS for all endpoints and enable it just for adminlog api for now. 

* Domain in api. 

* Better account type selection in parse_auth_id. 

* Typo & imports. 

* Typo del: unused function. 

* Init_db filling user/admin username|passowrd fields. 

* Fill username & password in user/admin creation. 

* Bug. 

* Bug & authenticate api calls with session cookie. 

* New.html assests link. 

* Backward compatibility. 

* Bug. 

* First try to authenticate with HTTP Authorization header value then check the user session data. 
  _Think user is authenticated as A1 then they want to login as A2 on same
domain. in this case we should keep our eye on header not session.
because session is authenticated by A1 but now we want to authenticate
with A2_

* /admin/adminuser/ links username password bug. 

* Fix: accept authentication link to login(eg. https://username:password@domain.com/path) 

* No need to send g.proxy_path to templates (jinja has it) 

* Merging conflicts. 

* Status js log file call to use api. 

* Bug. 

* Creating empty session(in redis) for every request. 

* Unboundlocalerror bug. 

* Remove links with uuid. 

* Admin link in invalid proxy. 

* Backward compatibility. 

* Setup session data for admin. 

* Using g.account instead of g.user/g.admin. 

* Add authentication(role-based) for ModelView classes. 

* Basic authentication verify password function. 

* Rename. 

* Short_api. 

* Info api profile title. 

* Typo. 

* Profile name. 

* Remove run commander.py with "sudo python3" 

* Backup restoring. 

* Bug and refactor. 

* Bug. 

* Run_commander.py. 

* User apis bugs. 

* Typo. 

* Mistake. 

* Ip_utils imports. 

* Get_interface_public_ip (return [] instead of None) 

* Init_db bug. 

* Xui importer. 

* Ios bug. 

* Exception handle. 

* Bugs. 

* Import bug. 

* Bug and add description. 

* Change expire_in variable from minutes to seconds. 

* Hiddify_next.ico. 

* Bug in apiflask. 

* Security issue. 

* Bug. 

* Bug. 

* Heart icon. 

* Bug in user 'me' api. 

* Flask_migrate common errors. 

* Could not build url for endpoint 'admin.static' error. 

* Https://github.com/hiddify/HiddifyPanel/pull/45#discussion_r1390457377. 

* Https://github.com/hiddify/HiddifyPanel/pull/45#discussion_r1390456353. 

* User short link showing page. 

* Typo. 

* Proxy not updated  after delete. 

* Bug. 

* Security concern. 

* Permission issue. 

* Bug in new domain. 

* Domains not removed. 

* Domains in mtproxy. 

* Bug in user.py. 

* Get telegram bot in get_common_data method. 

* Backup restore. 

* Bug in report issue. 

* Multiple ip. 

* Common.py bug. 

* Admin link. 

* Admin link bug. 

* Bug in decoy selector. 

* Bug in clean install. 

* Typo. 

* Not preserving admin uuid when upgrade. 

* Bug. 

* Vmess bug. 

* Branding free text. 

* Grpc bug in singbox. 

* Grpc h2 bug. 

* Reality grpc  bug in singbox. 

* Telegram admin bot bug. 

* Bug in error report. 

* Reality bug. 

* Bug. 

* Agent bug. 

* Bug. 

* Bug. 

* User add bug. 

* Grpc bug. 

* Bug. 

* No commit message. 

* Typo. 

* Hysteria link. 

* Translation issue. 

* Typo. 

* Ipv6 ::1. 

* Bug in not restoring allowed subdomain. 

* Search and sort in user page. 

* Change in modes. 

* Bug in port. 

* Proto. 

* Tls bug. 

* Bug. 

* Typo. 

* Bug. 

* Bug in get singbox active users. 

* Setting issue. 

* Always shows error in dev version. 

* Child id. 

* Bug in cyclic loop. 

* Bugs in upgrading database. 

* Update enums automatically. 

* Owner. 

* Short. 

* Import old configs bug. 

* Shadowtls singbox. 

* Bugs. 

#### Other

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Inlang: update translations. 

* Temporary change restart for telegram proxies. 

* Merge pull request #151 from Iam54r1n4/dev-patch27. 
  _Fix telegram proxy bug_

* Update config_enum.py. 

* Update. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Inlang: update translations. 

* Update  translation. 

* Inlang: update translations. 

* Update. 

* Inlang: update translations. 

* Update. 

* Update translation. 

* Update. 

* Update translation. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Merge pull request #149 from Mrclocks/main. 
  _Update translations_

* Inlang: update translations. 

* Merge pull request #150 from Iam54r1n4/dev-patch26. 
  _Fix bugs_

* Merge pull request #148 from Iam54r1n4/dev-patch24. 
  _Fix bugs_

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Inlang: update translations. 

* Makeing unified version. 

* Disable changing proxy details. 

* Merge pull request #147 from Iam54r1n4/fix-tg-bot. 
  _Fix setting telegram web hook_

* Reformat. 

* Disable csrf globally. 

* Merge pull request #145 from Iam54r1n4/up-trans. 
  _inlang: update translations: fix missing translations_

* Merge branch 'main' into up-trans. 

* Add modal for quicker editing. 

* Inlang: update translations. 

* Update translation. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Inlang: update translations. 

* Merge branch 'hiddify:main' into up-trans. 

* Inlang: update translations. 

* Update translation. 

* Inlang: update translations. 

* Inlang: update translations. 

* Update translations. 

* Update. 

* Update translations. 

* Inlang: update translations. 

* Update translations. 

* Merge pull request #144 from Iam54r1n4/fix-babel-translation. 
  _Fix extracting babel .pot file data from the html files_

* Merge pull request #143 from Iam54r1n4/dev-patch23. 
  _Fix update usage bug_

* Merge pull request #142 from Iam54r1n4/dev-patch23. 
  _Fix url encoding & decoy domain in first setup_

* Improve: better url encoding. 

* Merge pull request #141 from Iam54r1n4/dev-patch22. 
  _Fix all-configs api bug_

* Temporaryfix of translations. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Merge pull request #138 from Iam54r1n4/dev-patch19. 
  _Fix showing force cdn_

* Merge pull request #139 from Iam54r1n4/dev-patch20. 
  _Fix vless trojan protocol headerType parameter in streisand_

* Update link_maker.py. 

* Improve: condition. 

* Merge pull request #137 from Iam54r1n4/dev-patch18. 
  _Fix admin log bug & refactor code_

* Del: unused import. 

* Merge branch 'main' into dev-patch18. 

* Merge pull request #136 from Iam54r1n4/dev-patch17. 
  _Dev patch17_

* Merge pull request #135 from Iam54r1n4/dev-patch16. 
  _Fix telegram_enable field in api_

* Chg. 

* Merge pull request #134 from Iam54r1n4/dev-backup. 
  _add: childs to backup_

* Add: childs to backup. 

* Merge pull request #133 from Iam54r1n4/dev-backup. 
  _fix: develop backup bug_

* Merge branch 'main' into dev-backup. 

* Disable basic auth due to unsupported by safari. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Merge pull request #128 from Iam54r1n4/wireguard-driver. 
  _Add wireguard driver_

* Update wireguard_api.py. 

* Chg. 

* Merge branch 'hiddify:main' into wireguard-driver. 

* Merge pull request #132 from Iam54r1n4/dev-patch15. 
  _fix: fragemnt_

* Merge branch 'hiddify:main' into wireguard-driver. 

* Merge pull request #131 from Iam54r1n4/dev-patch14. 
  _fix: wireguard key generation_

* Chg. 

* Add: wireguard driver. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Merge pull request #129 from Iam54r1n4/dev-patch12. 
  _Add user name to configs links_

* Add: user name to profile url. 

* Add: user name to configs links. 

* Merge pull request #130 from Iam54r1n4/dev-patch13. 
  _Fix import bug_

* Update translations andd db version. 

* Update translation. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Merge pull request #127 from Iam54r1n4/dev-patch11. 
  _fix: singbox fg parameter sending_

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Merge pull request #126 from Iam54r1n4/dev-patch10. 
  _Delete admin telegram_proxy_enable & speedtest_enable api fields_

* Del: admin telegram_proxy_enable & speedtest_enable api fields. 

* Remove any refere from urls. 

* Merge pull request #125 from Iam54r1n4/dev-patch10. 
  _Add speetest & telegram proxy availability to api_

* Add: speetest & telegram proxy availability to admin "/me" api. 

* Add: speetest & telegram proxy availability to user "/me" api. 

* Merge pull request #123 from Iam54r1n4/dev-patch7. 
  _fix: ua bug_

* Merge branch 'main' into dev-patch7. 

* Merge pull request #124 from Iam54r1n4/dev-patch9. 
  _Fix fragmentation & mux_

* Merge branch 'main' into dev-patch9. 

* Remove user_agent cache and fix typo. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Merge pull request #122 from Iam54r1n4/dev-patch9. 
  _Fix mtproxies link_

* Merge pull request #121 from Iam54r1n4/dev-patch8. 
  _Fix backup restoring & auto ip selector bug_

* Merge pull request #119 from Iam54r1n4/dev-patch6. 
  _Fix show sub link as profile url_

* Chg. 

* Merge pull request #120 from Iam54r1n4/dev-patch7. 
  _Fix wireguard link_

* Chg. 

* Chg. 

* Merge pull request #117 from Iam54r1n4/dev-patch4. 
  _Fix bug in downloading backup_

* Merge pull request #118 from Iam54r1n4/dev-patch5. 
  _Show log in status page by default_

* Merge pull request #116 from Iam54r1n4/dev-patch3. 
  _Fix getting log file after quick setup_

* Merge pull request #115 from Iam54r1n4/dev-patch2. 
  _Fix db bool/str config tables bug_

* Update translations. 

* Refactor elements in useradmin. 

* Merge pull request #114 from Iam54r1n4/dev-patch. 
  _Fix bugs/typos_

* Merge pull request #113 from Iam54r1n4/bug-fix. 

* Fix bugs. 

* Enable cache again. 

* Big refactor. 

* Increase session lifetime to 10 days. 

* Merge. 

* Merge pull request #111 from Iam54r1n4/fix-mtproxy. 
  _fix: mtprotoproxy library link_

* Merge pull request #109 from Iam54r1n4/fix-xray-fg. 
  _fix: fragmentation_

* Merge pull request #110 from Iam54r1n4/bug-fix. 
  _Fix client app icon bug_

* Merge pull request #107 from Iam54r1n4/refactor_configenum. 
  _Complete configenum refactoring_

* Refactor: configenum complete. 

* Merge pull request #106 from Iam54r1n4/refac-configenum. 
  _Refactor config_enum_

* Update config_enum.py. 

* Refactor: config enum. 

* Merge pull request #105 from Iam54r1n4/tel_bug. 
  _fix: telegram sending msg bug & babel_

* Force https and basic auth for admins. 

* Update cache to 3.0.0. 

* Merge pull request #101 from Iam54r1n4/bug-fix. 
  _Fix telegram_id bug_

* Merge pull request #102 from Iam54r1n4/refactor-xui_importer. 
  _Refactor xui importer_

* Merge branch 'main' into refactor-xui_importer. 

* Merge pull request #103 from Iam54r1n4/refactor-hiddifypy. 
  _Refactor hiddify.py and hutils_

* Refactor: hiddify.py & type hint. 

* Refactor: network. 

* Refactor: hiddify.py system. 

* Refactor: xui importer. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Merge pull request #100 from Iam54r1n4/refactor-hutils. 
  _Refactor hutils_

* Refactor: github issue generator. 

* Refactor: hutils/hiddify flask & fix bug. 

* Merge pull request #99 from Iam54r1n4/refactor-hutils. 
  _Refactor hutils_

* Refactor: hutils convert. 

* Refactor: hutils random. 

* Refactor: hutils encode. 

* Refactor: hutils auth. 

* Refactor: hutils json. 

* Disable proxy create. 

* Add uwsgi to req. 

* Merge pull request #96 from Iam54r1n4/xray-cfg. 
  _Add tls fragmentation & mux parameters to subscription's links for xray_

* Add: tls fragmentation & mux parameters to subscription's links for xray. 

* Merge pull request #97 from Iam54r1n4/singbox-mux. 
  _Fix bug in sending singbox client's config_

* Merge pull request #95 from Iam54r1n4/singbox-mux. 
  _Add Singbox multiplex & tls_fragment object to configs (client-side)_

* Add: tls padding to singbox client's config. 

* Merge branch 'singbox-mux' of github.com:Iam54r1n4/HiddifyPanel into singbox-mux. 

* Merge branch 'hiddify:main' into singbox-mux. 

* Add: tls fragment to singbox client side config file if the client supports. 

* Add: singbox multiplex object to configs (client-side) 

* Remove sysout. 

* Refactor: account and others. 

* Update. 

* Update lang. 

* Merge pull request #94 from Iam54r1n4/fix-agent-role. 
  _fix: agent admin permission_

* Merge pull request #91 from Iam54r1n4/new-links. 
  _Add new config endpoints_

* Merge pull request #92 from Iam54r1n4/fix-lang. 
  _Fix lang_

* Add: new config links. 

* Merge pull request #93 from Iam54r1n4/tel_bug. 
  _Fix telegram id bugs_

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Merge pull request #89 from Iam54r1n4/mux. 
  _Add multiplexer config fields_

* Change defaults for mux. 

* Fix the locale generated dynamically. 

* Add: validation for mux fields. 

* Add: db version for mux fields. 

* Add: mux new fields. 

* Merge pull request #90 from Iam54r1n4/tel_bug. 
  _Fix sending message to user in with telegram bot_

* Merge pull request #88 from Iam54r1n4/validation. 
  _Add validation for tls tricks and  hysteria new fields_

* Add: validation for hysteria fields. 

* Add: tls tricks validations. 

* Better singbox config. 

* Remove: print. 

* Merge pull request #87 from Iam54r1n4/hysteria2. 
  _Hysteria2 link maker dynamically with DB (client side link)_

* Add: todo. 

* Merge pull request #86 from Iam54r1n4/hysteria2. 

* Add: hysteria2 setting to database. 

* Merge pull request #85 from Iam54r1n4/tls-trick. 
  _Bug fix_

* Merge pull request #84 from Iam54r1n4/domain-chg. 

* Add: extra_params field to domain model. 

* Merge pull request #83 from Iam54r1n4/tls-trick. 
  _add: tls fragment fields_

* Add: tls_trick config category. 

* Add: tls fragment fields in db. 

* Merge pull request #82 from Iam54r1n4/bug-fix. 

* Update: ui. 

* Remove geoip for singbox 1.8. 

* Merge. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Merge pull request #81 from er888kh/patch-3. 
  _Update hiddify.py_

* Update hiddify.py. 
  _Guard against concatenation with non-string host values (such as IP address)_

* Remove temporary access, refactor panel links, refactor user.py. 

* Merge pull request #76 from Iam54r1n4/refactor-proxy. 
  _Refactor proxy model_

* Merge pull request #77 from Iam54r1n4/refactor-parent-domain. 
  _Refactor parent domain_

* Merge branch 'main' into refactor-parent-domain. 

* Merge pull request #80 from Iam54r1n4/refactor-daily-usage. 
  _Refactor DailyUsage model_

* Login by uuid@domain.com/path/l. 

* Remove old user_agent. 

* Merge pull request #78 from Iam54r1n4/fix-auth. 
  _fix: typo_

* Merge branch 'main' into fix-auth. 

* Update ui. 

* Update ui. 

* Update translation. 

* Update version. 

* Merge pull request #74 from Iam54r1n4/auth. 
  _Better role management & api validating/parenting/recursiving & refactoring models_

* Merge branch 'auth' of github.com:Iam54r1n4/HiddifyPanel into HEAD. 

* Merge pull request #73 from Iam54r1n4/auth. 
  _Auth_

* Merge branch 'hiddify:main' into auth. 

* Merge pull request #72 from Iam54r1n4/auth. 
  _Implement session authentication (removing uuid from url)_

* Add: AccountType enum for sake of readability(will be used more) 

* Del: duplicate function. 

* Add: get by username password. 

* Del: unused var. 

* Using: proper using of proxy path (for panel links) 

* Clean: unused var. 

* Add: new fields to str_config(proxy paths) 

* Del: using g.account.uuid instead of g.account_uuid. 

* Refactor. 

* Add: user/pass to hiddifypanel admin-links command(cli) 

* Add: user/pass to user admin links. 

* Clean up. 

* Add: login_required to quicksetup. 

* Add: authentication for user panel. 

* Add: user:pass to non-secure link too. 

* Add: user:pass to /admin/adminuser/ links. 

* Add: new format of domain showing (https://user:pass@domain.com) 

* Add: get current logged account apikey (draft) 

* Merge commit '26b0713eba52700902e5b530b62a276e3d7dae0a' into auth. 

* Using: new login_required. 

* Add: role property to user and admin models & implement Role enum new: override user/admin get_id method. 

* Using flask_login instead of old authenticator. 

* Add: flask_login & add flask_login.UserMixin to User and AdminUser models. 

* Support app changes. 

* Add: CORS for javascript calls. 

* Add: admin log api. 

* Add: auth for apps api. 

* Merge branch 'auth' of github.com:Iam54r1n4/HiddifyPanel into auth. 

* Merge pull request #71 from Iam54r1n4/fix-apps-api. 
  _fix: unboundlocalerror bug_

* Update ui. 

* Merge pull request #70 from Iam54r1n4/main. 
  _fix: info api profile title & short api expire time_

* Add: server-side(redis) session instead of client-side. 

* Add: redirect_to_user.html. 

* Add: role authentication for views. 

* Add: api auth, basic auth, old url backward compatibility middlewares chg: g.user and g.admin to g.account. 

* Add: some functions in utils. 

* Add: admin route backward compatibility. 

* Add: athentication with session. 

* Using non-assci name in building username because we send username and password with base64 encoding, so we're not limited to assci. 

* Add: auth to admin panel endpoints. 

* Refactor: user apis. 

* Add: get_user_roles to authentication.py. 

* Add: auth to admin apis. 

* Add: username & password to user model and admin model - filling the username and password (password saved in database as   plaintext) 

* Add: auth to api (incomplete) 

* Update ui. 

* Merge pull request #69 from Iam54r1n4/main. 
  _fix: profile title_

* Merge branch 'hiddify:main' into main. 

* Merge branch 'main' of github.com:Iam54r1n4/HiddifyPanel. 

* Update ui. 

* Update. 

* Merge pull request #68 from Iam54r1n4/main. 

* Merge branch 'hiddify:main' into main. 

* Update. 

* Merge branch 'main' of github.com:hiddify/Hiddify-Panel. 

* Merge pull request #67 from Iam54r1n4/commander. 

* Update ui. 

* Merge pull request #66 from Iam54r1n4/commander. 
  _Using commander.py_

* Merge branch 'hiddify:main' into commander. 

* Merge pull request #65 from Iam54r1n4/xui_importer. 

* Update: cli. 

* Update: using commander.py apply-user instead of running install.sh apply_users directly. 

* Update: apply_users command. 

* Update: using commander.py get-cert instead of using get-cert.sh directly. 

* Update: run_commander. 

* Merge pull request #64 from Iam54r1n4/fix-user-apis. 
  _Fix user apis_

* Add: nekobox app to ../apps/ api (in android platform) 

* Update version. 

* Update ui. 

* Add new ui. 

* Merge pull request #61 from Iam54r1n4/main. 
  _refactor: utils and other things_

* Add: version parameter type. 

* Move clean_ip to hutils/auto_ip_selector better imports. 

* Refactor: add types to funcitons. 

* Del: myip & myipv6 variables. 

* Merge pull request #60 from Iam54r1n4/main. 
  _fix: init_db bug_

* Merge pull request #59 from Iam54r1n4/xui_importer. 
  _Xui importer_

* Add: xui importer cli. 

* Add: xui importer. 

* Update translations. 

* Update translations. 

* Install app. 

* Update. 

* Merge pull request #56 from er888kh/main. 
  _Check all IP addresses while adding a domain_

* Make public ip finding more robust. 

* Check all ip addresses when adding domains. 

* Add missing dependency. 

* Merge pull request #58 from Iam54r1n4/main. 
  _fix: import bug_

* Merge pull request #53 from Iam54r1n4/refactor_api. 
  _Refactor user & admin APIs_

* Del: unnecessary imports. 

* Add: description to api schemas. 

* Refactor: admin APIs. 

* Refactor: user APIs. 

* Merge pull request #52 from Iam54r1n4/reform_apps_api. 
  _Reform apps api_

* Merge branch 'reform_apps_api' of github.com:Iam54r1n4/HiddifyPanel into reform_apps_api. 

* Merge pull request #51 from Iam54r1n4/reform_apps_api. 
  _Reform apps api_

* Merge branch 'hiddify:main' into reform_apps_api. 

* Merge pull request #50 from Iam54r1n4/reform_apps_api. 
  _Reform apps api_

* Reform: apps api. 

* Merge pull request #48 from Iam54r1n4/main. 
  _Add apps api_

* Reform: apps api. 

* Add: client apps icon for apps api. 

* Api things - change dto suffixes to Schema - add apps api - add expire_in field in short api. 

* Merge branch 'main' of github.com:Iam54r1n4/HiddifyPanel. 

* Merge branch 'hiddify:main' into main. 

* Merge pull request #47 from MichaelUray/main. 
  _Update UserAdmin.py_

* Update UserAdmin.py. 
  _Shows Telegram icons for all users in the admin panel, if Telegram is enabled.

Users which are not registered for Telegram are shown with greyed out disabled buttons, registered users with blue buttons.
It is a visual improvement to have all users aligned in the table._

* Merge branch 'main' of github.com:Iam54r1n4/HiddifyPanel. 

* Merge branch 'hiddify:main' into main. 

* Add: 'api/v2/admin/server_status/ api. 

* Add: "lang" field to admin '/me/' api DTO. 

* Create database tables with flask_migrate. 

* Add: "api/v2/admin/me" & "api/v2/user/me" api. 

* Merge pull request #46 from Iam54r1n4/main. 
  _remove UserLang duplicated defination_

* Remove duplicated definations. 

* Merge pull request #45 from Iam54r1n4/main. 
  _Complete user api_

* User area APIs tested and fixed. 

* Edit: create a jinja template for github isuee. 

* Add: lang field to User model. 

* Merge pull request #44 from er888kh/patch-1. 
  _Update requirements.txt_

* Update requirements.txt. 
  _Add missing dependency flask-apispec_

* Update. 

* Add def lang to info and tags to all-configs. 

* Better mtproxy. 

* Review code. 

* Merge pull request #42 from Iam54r1n4/main. 

* Merge github.com:hiddify/HiddifyPanel Add user.py api. 

* Fix typo. 

* Refactor github issue things. 

* Merge branch 'main' of github.com:Iam54r1n4/HiddifyPanel. 

* Add json5. 

* Hide v2ray configs. 

* Rm old. 

* Add six. 

* Add default warp_sites. 

* Merge branch 'main' of github.com:Iam54r1n4/HiddifyPanel. 

* Fix version in the dependencies. 

* Change name to hiddify manager. 

* Add po to json convertor. 

* Update name to hiddify manager. 

* Merge pull request #41 from Iam54r1n4/main. 
  _Internal server error issue_

* Feature: implement issue generator for internal server error (500.html) 

* Add: github_issue_generator.py. 

* Merge pull request #40 from pjrobertson/main. 
  _Translation Improvements_

* Further translation improvements. 

* Fix Chinese User UI for iOS + English slight modification. 

* Merge pull request #39 from pjrobertson/main. 
  _中国人 > 简体中文_

* 中国人 > 简体中文. 

* Remove: release_old. 

* Add tuic and hysteria to configs. 

* Fix. 

* Add hidden char. 

* Remove reality servernames as it is not really useful. 

* Add hysteria2 link. 

* Merge branch 'main' of github.com:hiddify1/HiddifyPanel. 

* Merge pull request #32 from elia07/hiddifyDevelop. 
  _fix creating new user via api, add delete api for deleting users_

* Fix creating new user via api, add delete api for deleting users. 

* Merge pull request #29 from er888kh/main. 
  _Generate X25519 keys using `python-cryptography`_

* General code refactor and optimization. 
  _Improve UUID checking_

* Optimize more imports. 

* Optimize imports. 

* Generate X25519 keys using `python-cryptography` 

* Remove not needed configs. 

* Update tuic link. 

* Update master. 

* Update tuic. 

* Remove utls in tuic and hystria. 

* Add tuic link and clashmeta. 

* Fix zero. 

* Add no-gui for update. 

* Merge branch 'v8' 

* Better upgrading database. 

* Better manage override admin. 

* Merge branch 'main' of github.com:hiddify1/HiddifyPanel. 

* Merge pull request #26 from mortza/fix-api-endpoints. 
  _Fixed filtering resources_

* Fixed filtering resources. 
  _Fixed user and admin filtering using get parameter_

* Merge pull request #23 from er888kh/main. 
  _Block QUIC to improve performance_

* Fix formatting. 

* Block QUIC to improve performance. 

* Update to v8 changes. 

* Merge branch 'v8' 

* Disable cache during update. 

* Convert old db to new. 

* Add pysql req. 



## 8.8.99 (2024-03-02)

#### Fix

* Bug (latest release on v8) 



## 8.8.96 (2024-02-21)

#### New

* Add more security for first setup. 

#### Fix

* Log file name bug. 

#### Other

* Merge pull request #104 from Iam54r1n4/v8. 
  _fix: log file name bug_



## 8.8.95 (2024-01-22)

#### Fix

* No admin bug. 



## 8.8.94 (2024-01-16)

#### Fix

* Singbox1.8. 



## 8.8.93 (2024-01-15)

#### Other

* Better singbox config. 



## 8.8.92 (2024-01-14)

#### Fix

* Bug for hiddify next. 



## 8.8.91 (2024-01-13)

#### Fix

* Bug in singbox. 



## 8.8.9 (2024-01-13)

#### Fix

* Bug in singbox 1.8. 



## 8.8.8 (2024-01-09)

#### Fix

* User agent issue for singbox 1.7 and hiddify next. 



## 8.8.7 (2024-01-09)

#### Fix

* Singbox 1.8 issue. 



## 8.8.6 (2024-01-09)

#### Fix

* Not import in hiddify bug. 



## 8.8.5 (2024-01-09)

#### Fix

* Bug in user agent. 



## 8.8.3 (2024-01-09)

#### New

* Add auto support for singbox 1.8 and 1.7. 

#### Fix

* Validation error bug. 

#### Other

* Merge pull request #62 from Iam54r1n4/v8. 
  _fix: validation error bug_



## 8.8.2 (2023-11-26)

#### Other

* Merge pull request #57 from Iam54r1n4/v8. 
  _fix bug in admin.py_

* Fix bug in admin.py. 

* Merge pull request #55 from Iam54r1n4/v8. 
  _fix bug in admin.py_

* Fix bug in admin.py. 



## 8.8.1 (2023-11-22)

#### Other

* Allow incompatible server names for reality. 



## 8.8.0 (2023-11-22)

#### Other

* NEW: allow reality to be incorrect. 



## 8.7.1 (2023-11-02)

#### Fix

* Bug. 



## 8.7.0 (2023-11-02)

#### Fix

* Api issues and resolve security issue. 



## 8.6.11 (2023-10-19)

#### Fix

* Req issue. 



## 8.6.8 (2023-10-12)

#### Fix

* Bug in russian lang. 



## 8.6.7 (2023-10-12)

#### New

* Add russian translation. 

#### Fix

* Add domain bug. 



## 8.6.6 (2023-10-08)

#### Changes

* Update hiddify next links. 



## 8.6.4 (2023-10-06)

#### New

* Add hidden chars. 

#### Fix

* Bug in translation. 



## 8.6.2 (2023-10-02)

#### Fix

* Backup? 

* Has update. 



## 8.6.1 (2023-09-13)

#### Other

* Link to right repo. 



## 8.6.0 (2023-09-13)

#### New

* Add beta release. 

#### Fix

* User count in sub admins. 

* Restore multiple admin types. 



## 8.5.3 (2023-09-12)

#### Fix

* Bug. 



## 8.5.2 (2023-09-12)

#### New

* Add reality h2. 



## 8.5.1 (2023-09-12)

#### Fix

* Bug in change reality id. 

* Translation. 



## 8.5.0 (2023-09-11)

#### Fix

* Backup, override owners. 

* Port already used. 

#### Other

* Fix api get uuid. 

* Update to latest hiddify next release. 



## 8.4.2 (2023-09-09)

#### Fix

* Autocdn ip. 



## 8.4.1 (2023-09-09)

#### New

* Add singbox user detector. 



## 8.4.0 (2023-09-08)

#### Fix

* Speed issue. 

* Speed issue in adding users. 



## 8.3.9 (2023-09-06)

#### Fix

* TB bug. 



## 8.3.8 (2023-09-04)

#### Fix

* V2ray typo. 



## 8.3.7 (2023-09-04)

#### New

* Change usage to TB if more than 1TB. 

#### Fix

* V2ray config. 



## 8.3.6 (2023-09-03)

#### Fix

* Bug in reality grpc apply config. 



## 8.3.5 (2023-09-03)

#### Fix

* Singbox bug. 



## 8.3.4 (2023-09-03)

#### Fix

* Reality singbox. 

#### Other

* Add Streisand deep link. 



## 8.3.3 (2023-09-02)

#### Changes

* Disable firewall by default. 

#### Other

* Add quic in singbox configs. 



## 8.3.2 (2023-08-31)

#### Fix

* Singbox hiddify. 

* Shadowsocks. 



## 8.3.1 (2023-08-31)

#### Fix

* Manifest bug. 

#### Other

* Adding ssh singbox config in all configs. 

* Remove last_version. 



## 8.3.0 (2023-08-31)

#### Other

* Invalidate cache in start. 



## 8.2.4 (2023-08-31)

#### Other

* Disable indexing by search engings. 

* Remove user secret from static files. 

* Make sure cache will be empty. 



## 8.2.3 (2023-08-30)

#### Other

* Fox" bug. 



## 8.2.2 (2023-08-30)

#### Fix

* Typo for quick settings. 



## 8.2.1 (2023-08-30)

#### Fix

* Short link. 



## 8.2.0 (2023-08-30)

#### Fix

* Utls in shadowtls. 



## 8.1.9 (2023-08-30)

#### Other

* Fix singbox comment. 

* Remove profile name. 



## 8.1.8 (2023-08-30)

#### Other

* Remove ssh singbox from all-configs. if your ssh server is enable your user can still use this link until next release. 



## 8.1.7 (2023-08-30)

#### Fix

* Multiple qrcode. 

#### Other

* Fix tag. 



## 8.1.6 (2023-08-30)

#### New

* Add prerelease. 

#### Fix

* One click qrcode. 

* Typo. 

* Prerelease. 

* Tag version. 

#### Other

* Test. 



## 8.1.4 (2023-08-30)

#### Other

* Better downgrade. 



## 8.1.3 (2023-08-30)

#### Other

* Show short link url. 



## 8.1.2 (2023-08-30)

#### Fix

* Disable user bug. 



## 8.1.1 (2023-08-30)

#### Fix

* Bug in disabling users. 



## 8.1.0 (2023-08-30)

#### Fix

* Download issue. 

#### Other

* Disable name in configs. 



## 8.0.3 (2023-08-29)

#### Other

* Use singbox config in hiddifynext. 

* Optimize get configs. 



## 8.0.2 (2023-08-29)

#### New

* Add download directly from github. 



## 8.0.1 (2023-08-29)

#### Other

* Better error logs. 

* Better fix. 



## 8.0.0 (2023-08-29)

#### New

* Disable cache on error. 

* Add short link for ease user access. 

* Add unified link. 

* Add auto page. 

* Add full singbox config. 

* Add UDP support for SSH. 

* Force user to double check decoy site. 

* Generate ssh key if empty. 

* Reset cache on change any config. 

* Change caching method to pickle. 

* Speed up the panel. 

* Speed up the panel by using redis. 

* Add auto button. 

* Add auto sub. 

* Add report analyser. 

* Add ssh keys to the backup. 

* Add ability to change reality keys. 

* Add unsigned https ip. 

* Better singbox config. 

* Add caching for speed up some process. 

* Add singbox config. 

* Add singbox config for ssh. 

* Add ssh server port. 

* Add ssh user support. 

#### Changes

* Remove access by https://ip if there is some domains. 

* Better singbox config. 

* Handle exception for redis. 

* Disable ui download. 

* Add dns to tcp. 

* Update usage. 

* Add restart on change ssh configs. 

* Remove ssh key info. 

* Disable caching. 

#### Fix

* Better open. 

* _ in the begin of profile name. 

* Caching error. 

* Rocket Loader. 

* Bug. 

* Bug in cache. 

* Usage info and sub. 

* Bug. 

* Font issue. 

* Rounding option in v2ray configs. 

* Ssh multiple time added. 

* Linux. 

* Lang issues. 

* Delay in updating proxies. 

* Ssh ip domain bug. 

* Ssh ip. 

* Bug. 

* Bug in secure link. 

* Bug in reality when asn failed. 

* Release message bug. 

* Clash config. 

* Singbox config. 

* Bug. 

* No commit message. 

* Bug in singbox. 

* Bug. 

* Singbox config issue. 

* Add remove bug. 

* Ssh keys json. 

* Bug. 

* Ssh config. 

* Bugs. 

* Singbox api. 

* Bug in userusage. 

* Singbox comment. 

* Singbox. 

* Bool. 

* Remove client. 

* Singbox error. 

* Config issue. 

* Bug. 

* Bug. 

* Bug. 

* Typo. 

* Bug. 

* Ssh liberty redis path. 

#### Other

* Fix bug with rocket loader. 

* Fewer click in auto link. 

* Better translations. 

* Add unlimited usage. 

* Update translations. 

* Remove expire days from report if it is more than 1000 days or if usage limit is more than 100,000G. 

* Better display of user info in non hiddify apps. 

* Update link maker. 

* Translate to persian. 

* Set default stack to system. 

* Merge branch 'main' of github.com:hiddify1/HiddifyPanel. 

* Merge pull request #18 from randomguy-on-internet/main. 
  _fixing IPv6 issue for resolving IPv6's behind domain in auto cdn_

* Fixing IPv6 issue for resolving IPv6's behind domain in auto cdn. 
  _adding brackets to avoid errors when converting domains to ipv6.

aaaa:bbbb:cccc:dddd -> [aaaa:bbbb:cccc:dddd]_

* Fix; v2ray bug. 

* New; add ssh in sub link. 

* Update. 

* Update. 

* Merge branch 'main' of github.com:hiddify1/HiddifyPanel. 

* Merge pull request #17 from randomguy-on-internet/main. 
  _Reality utls bug_

* Utls bug. 
  _fixing utls bug for reality configs_

* Fix singbox ip. 

* FIX: 

* Merge branch 'main' of github.com:hiddify1/HiddifyPanel. 

* Merge pull request #14 from randomguy-on-internet/patch-1. 
  _clash GRPC bug_

* Update link_maker.py. 

* Update link_maker.py. 



## 7.2.0 (2023-08-05)

#### New

* Add  compatibility for downgrade for ssh. 



## 7.1.9 (2023-07-30)

#### Fix

* Bugs. 



## 7.1.8 (2023-07-30)

#### Other

* Update license. 

* Update license. 



## 7.1.7 (2023-07-30)

#### Other

* Update. 



## 7.1.6 (2023-07-30)

#### New

* Update to open source. 

#### Other

* Apply formating. 



## 7.1.3 (2023-06-14)

#### New

* Remove old runs. 

#### Fix

* Reset bug. 

#### Other

* Add manually. 



## 7.1.2 (2023-06-13)

#### Other

* Update translation. 



## 7.1.1 (2023-06-13)

#### Fix

* Cpu percentage. 



## 7.1.0 (2023-06-13)

#### Fix

* Setting not saved. 

* Restart. 

* Loading issues. 

#### Other

* Update. 



## 7.0.9 (2023-06-04)

#### Fix

* Domain mode. 



## 7.0.8 (2023-06-04)

#### New

* Group modes. 



## 7.0.7 (2023-06-04)

#### New

* Remove gov websites from decoy sites. 

* Add domain fronting to the domains. 

#### Fix

* Telegram section will be displayed only when the domain. 

* Revert. 



## 7.0.6 (2023-05-30)

#### Fix

* Domain. 



## 7.0.5 (2023-05-30)

#### Fix

* Backup. 

* Ping. 

* Backup domains. 



## 7.0.4 (2023-05-30)

#### Fix

* Home not loading. 



## 7.0.3 (2023-05-29)

#### New

* If some configs are removed add them. 

* Remove old access. 

#### Fix

* Removing faketls domain. 

#### Other

* Remove grpc. 

* Remove grpc. 



## 7.0.2 (2023-05-29)

#### Fix

* Exception. 



## 7.0.1 (2023-05-29)

#### Fix

* Install bugs. 



## 7.0.0 (2023-05-29)

#### New

* Update panel. 

* Now get video from youtube if fail get it from local. 

* Add rest api. 

* Update lang. 

* Disable tcp mode. 

* Add more things. 

* Add head request. 

* Add head request. 

* Add head request. 

* Update backup with the new domains. 

* Add singbox usage. 

* Add notes for domain selection and add grpc reality. 

* Update lang. 

* Gun mode for grpc. 

* Fix ip behind cdn. 

* Add singbox api. 

* Remove hiddify:// on copy. 

* Do not inverse logs. 

* Add downgrade. 

* Add core selector. 

* Show error when autocdn format has problem. 

* Add reality. 

* Add worker domain. 

* Add multi domain reality, add core selector. 

* Add pt lang. 

#### Changes

* FirstAdmin->owner. 

#### Fix

* Bug. 

* Worker bug. 

* Downgrade. 

* Quick-setup bug. 

* Sublink only links. 

* Singbox bug. 

* Subonly links. 

* Lastindexof. 

* Installation finished. 

* Bug. 

* Bug. 

* Bug. 

* Singbox only support one servername. 

* New reality issues. 

* Typo. 

* Bug. 

* Sort bug. 

#### Other

* Better display logs. 

* Add: X-Real-IP header. 

* Remove extra text in footer. 



## 6.5.4 (2023-05-09)

#### Fix

* Bug in sort by expire date. 

#### Other

* Merge branch 'main' of github.com:hiddify1/HiddifyPanel. 

* Update custom.css. 

* Update custom.css. 



## 6.5.3 (2023-05-06)

#### Other

* Better result. 



## 6.5.2 (2023-05-05)

#### New

* Add dns. 

#### Fix

* Colors and result dialog. 



## 6.5.1 (2023-05-05)

#### New

* Add color in output. 

#### Other

* Update: lang. 



## 6.5.0 (2023-05-05)

#### New

* Add mode for warp. 



## 6.4.2 (2023-05-04)

#### Changes

* Fix shadowtls. 

#### Other

* Remove shadow tls from sub link. 



## 6.4.1 (2023-05-04)

#### New

* Show notification. 



## 6.4.0 (2023-05-04)

#### New

* Add warp plus code. 

#### Fix

* Bug. 



## 6.3.0 (2023-05-04)

#### Other

* Fix translate. 

* Enable warp. 



## 6.2.1 (2023-05-04)

#### Fix

* Base64. 



## 6.2.0 (2023-05-04)

#### New

* Add button. 

* Auto redirect to quick setup if not setup. 

#### Fix

* V2rayng. 

* Bug. 



## 6.1.7 (2023-05-04)

#### New

* Add HiddifyNG google play link. 



## 6.1.6 (2023-05-04)

#### Other

* Update links. 



## 6.1.4 (2023-05-03)

#### Fix

* Persian user profile. 



## 6.1.3 (2023-05-03)

#### New

* Add fragment in url. 



## 6.1.2 (2023-05-03)

#### Other

* Temp disable fragment. 



## 6.1.1 (2023-05-03)

#### Fix

* V2rayng download link. 



## 6.1.0 (2023-05-03)

#### Other

* Add profile title. 



## 6.0.1 (2023-05-01)

#### Other

* Update lang. 



## 6.0.0 (2023-05-01)

#### New

* Add fragment. 

* Add hiddify ng. 

* Better. 

* Add hiddify. 

* Add fragment. 

* Allow cdn and relay to add as only panel domains. 

#### Fix

* Color. 

#### Other

* UPDATE LANG. 

* Fix. 

* Update lang. 

* Temporary remove auto ip display. 

* Update lang. 

* Only 10 second to propose domains. 



## 5.0.3 (2023-04-27)

#### New

* Change back ios. 



## 5.0.2 (2023-04-26)

#### Other

* Change color. 



## 5.0.1 (2023-04-26)

#### New

* Add usage in sublink. 



## 5.0.0 (2023-04-26)

#### Fix

* Domain type. 

#### Other

* Better adding domains. 



## 4.5.1 (2023-04-26)

#### Other

* Update hiddify clash. 



## 4.5.0 (2023-04-26)

#### New

* Add ipv6 in cf api. 

* Fix v2rayng. 

* Add disable button and new style. 

* Better result page. 

* Add minimum valid users. 

* Add ip limits. 

* Organize better. 

#### Fix

* Bugs. 

* Bug. 

* Reality and xtls clash. 

* Bugs in update. 

* Usage bug. 

* Bug. 

* Selection. 

* Reality. 

* Bug. 

* Update. 

* Bug. 

* Auto cdn in user links. 

* Min users. 

#### Other

* Add hiddify links. 

* Better backup. 

* Fix. 

* Fix. 

* Fix. 

* Fix import. 



## 4.3.1 (2023-04-21)

#### Fix

* Backup date. 



## 4.3.0 (2023-04-21)

#### New

* Apple Colors. 



## 4.2.9 (2023-04-21)

#### New

* Super user infinit users. 



## 4.2.8 (2023-04-21)

#### Fix

* Bug. 



## 4.2.7 (2023-04-21)

#### Fix

* Sysout. 

* Typo. 



## 4.2.6 (2023-04-21)

#### New

* Priority in sublink only link. 



## 4.2.5 (2023-04-21)

#### Fix

* User. 



## 4.2.4 (2023-04-21)

#### Fix

* Backup bug. 

* Release issue. 



## 4.2.1 (2023-04-21)

#### Fix

* Usage. 



## 4.2.0 (2023-04-21)

#### New

* Click on admin. 

* Sub admins can have limits. 



## 4.1.2 (2023-04-20)

#### Fix

* No commit message. 



## 4.1.1 (2023-04-20)

#### Fix

* Bug. 



## 4.1.0 (2023-04-20)

#### New

* Fix backup. 

* Add permission for admin. 

#### Other

* Check datetime. 



## 4.0.5 (2023-04-19)

#### New

* Update. 

#### Fix

* Usage not counted. 



## 4.0.4 (2023-04-19)

#### Fix

* Alias. 



## 4.0.3 (2023-04-19)

#### Fix

* Xtls. 



## 4.0.2 (2023-04-19)

#### Fix

* Check proxy add. 



## 4.0.1 (2023-04-19)

#### Fix

* Bug. 



## 4.0.0 (2023-04-19)

#### New

* Telegram error check. 

* Change slave to agent. 

* Verify reality configs correctness. 

* Add warning for reality. 

* Disable warning to close. 

* Add telegram messages. 

* Send message to clients. 

* Reality is comming. 

* Add reality. 

* Ask before doing actions. 

* Better domain manager. 

* Hirarchy admin. 

* Multiple admin level, seperated usage per admin, parent_panel, backup to telegram, send message to telegram. 

* Add parent panel. 

#### Fix

* 7days. 

* Flow. 

* Bug in adding special char. 

* Flow bug. 

* Reality xtls. 

* No commit message. 

* Unsupported reality. 

* Update. 

* Permission erros and coutdown in persian error. 

* Telegram bot. 

* Bug. 

* Bug. 

#### Other

* Check. 

* Test: reality domains. 

* Chack organizarion name. 

* Add user link to msg. 

* Show warning for invalid alias. 

* Test: reality. 

* Add reality. 

* Add reality tag. 

* Update lang. 

* Remove speedtest. 

* Update to 1.8.1. 

* Fix. 

* Update: translation. 

* Fix bugs. 

* Update py. 



## 3.1.19 (2023-04-17)

#### Fix

* * domain. 



## 3.1.17 (2023-04-17)

#### Fix

* Bug in new installs. 



## 3.1.16 (2023-04-17)

#### Fix

* Fix new installation bug. 



## 3.1.15 (2023-04-17)

#### New

* Fix bug. 



## 3.1.14 (2023-04-16)

#### Fix

* Bot issue. 

#### Other

* Update. 



## 3.1.13 (2023-04-15)

#### Fix

* Loading dep. 



## 3.1.12 (2023-04-15)

#### Fix

* Bug. 

* Bug. 



## 3.1.10 (2023-04-15)

#### New

* Add confirmation before actions. 



## 3.1.9 (2023-04-15)

#### Other

* Fix. 



## 3.1.6 (2023-04-11)

#### Fix

* Yesterdays online. 



## 3.1.5 (2023-04-11)

#### New

* Fix the error in restoring configs. 



## 3.1.4 (2023-04-10)

#### Fix

* Bug. 



## 3.1.3 (2023-04-10)

#### Fix

* Issue with first setup. 



## 3.1.2 (2023-04-10)

#### Changes

* Add profile-web-page-url. 

#### Fix

* Persian ips. 

* Too much print. 



## 3.1.1 (2023-04-10)

#### Other

* Update. 



## 3.1.0 (2023-04-10)

#### New

* Optimize user changes. 

* Make footer in center for small devices. 

* Add more ips from ircf. 

#### Changes

* Change today's color. 

#### Fix

* Bot issue. 



## 3.0.9 (2023-04-09)

#### Fix

* Display issue of network. 

#### Other

* Update. 



## 3.0.8 (2023-04-09)

#### Fix

* Tgbot. 

#### Other

* Register bot if not registered. 

* Registerbot if not registered. 



## 3.0.7 (2023-04-09)

#### Fix

* G. 



## 3.0.6 (2023-04-09)

#### New

* Update translations. 

#### Other

* Force register bot if not registered. 



## 3.0.5 (2023-04-09)

#### Fix

* Folder size. 

* Versioning. 

* Bot add loading animation. 



## 3.0.4 (2023-04-09)

#### Fix

* Issues. 

* Issues. 



## 3.0.3 (2023-04-09)

#### Fix

* Error in changelog. 

#### Other

* Add auto cdn ip maker. 



## 3.0.2 (2023-04-09)

#### Other

* Remove change log. 



## 3.0.0 (2023-04-09)

#### New

* Show pwa notif only in home screen. 

* Update translation, remove tuic. 

* Fix package ended. 

* Add username in the link. 

* Add identify ip from X-Forwarded-For. 

* Auto update tails. 

* Add other country. 

* Search by english keyword in persian. 

* Remove netdata add history. 

* Add auto dark mode detector. 

* New sidebar. 

* Fix fingerprint. 

* Add darkmode. 

* Add new shatel. 

* Add wingsx. 

* Better user update usage. 

#### Changes

* Better style. 

#### Fix

* No commit message. 

* Style. 

* Daily, montly and weekly. 

* Vpn window for other countries. 

* Dark mode issues. 

* Progress bar. 

* Typo. 

* Last usage. 

* Usage. 

* Style. 

* No commit message. 

* No commit message. 

* Sidebar in xs. 

* Remaing days. 

* Big int issues. 

* Daily usage. 

* No commit message. 

* Do not show countdown in status. 

* Close boxes after search. 

* Bug. 

* Issues. 

* Bug. 

* Some updates. 

* Bug. 

* Template. 

* Pwa notification. 

* Dark mode issue. 

* No commit message. 

* Reset xray on model change. 

#### Other

* Update lang. 

* Disable netdata fix new user. 

* Add disbale user, network speed and more. 

* Remove sub links when package ended, add more and more. 

* Remove disk on small screens. 

* Show 3 column in big screens. 

* Update. 

* Add hiddify. 

* Remove test. 

* Add multiple process in dashboard. 

* Fix. 

* Fix big int. 

* Not using  * in ssl domains. 

* New; add support for * domains. add search in settings,fix bugs. 

* Update. 

* Fix the problem. 

* Fix bug. 

* Reduce build time. 

* Fix release message. 

* Commit all changes. 

* Add: cloudflare api. 



## 2.9.0 (2023-03-30)

#### New

* Select random operator if not detected. select random operator if multiple item exist. 

* Add notif when outdated. 

* Add asiatech. 

* Better information and fixed ip. 

* Add window only if cdn exist. 

* Fixing asn in sub link. 

* Show timer in apply configs. 

* Add ip info in sub link. 

* Add ip debug info in speed test. 

* Add backward compatibility. 

* Show version in error page. 

* Add clean ip support. 

* Add cloudflare api. if you add cloud flare api it will create or update domains automatically. 

* Add alias support for parent domain. 

* Central panel. 

* Disallow bot and search engines to access the site. 

* Add country for specific country needs. 

* Add restart action. 

* Auto reset if needed after changing configs. 

* Update. 

* Show notif on ios. 

* Add splash. 

* Same format. 

* Add splash screen. 

* Adding panel app :) 

* Increase user page size to 50. 

* Add encryption to vmess. 

* Add tls_h2 in sublinks. 

* Add h2 protocols. 

* Add encryption for vmess for better hidding traffic in http. 

* You can now remove port 80 and 443 from the proxies. 

* Convert old domain fronting configs to fake. 

* Open bot directly in telegram. 

* Open tgbot directly in telegram. 

* Add h2 support. 

* Add ios, none, edge, random to the utls settings. 

* Do not show http if http is diabled. 

* Add ports to all configs and in clash configs. 

* Make proxynames editable. 

* Add multiple ports. 

* Support multiple ports. 

#### Changes

* Ip only for auto cdn ip. 

* Better manage db init. 

* Better manage domains. 

* Show android webapp. 

* Remove  fingerprint. 

* Update android hiddify app. 

* Remove fingerprint. 

* Add get_domain. 

* Optimise link maker. 

* Move utls config to tls config. 

#### Fix

* No commit message. 

* Mokhaberat. 

* Error prune auto cdn ip. 

* Has cdn. 

* Zitel. 

* All errors. 

* Twitter. 

* Asn bug. 

* Video playback. 

* Cleanip. 

* Bug. 

* Error in access user page in some domains. 

* Description. 

* Backward compatibility. 

* Massive sysout. 

* Not showing all proxies. 

* Clean ip bug. 

* User ip. 

* Bug. 

* Auto cdn ip proxy. 

* Bugs. 

* Bug. 

* Bug. 

* Update. 

* Bug. 

* Resolve a problem. 

* Duplicate bug  in alias. 

* Configs in bot notworking. 

* Quick setup bug. 

* Bug in first install. 

* Show apply config on new domain. 

* Quicksetup bug. 

* Db init. 

* Telegram start. 

* New telegram bot format. 

* Bugs. 

* Compile issue. 

* Release. 

* Bugs. 

* Test. 

* Do not show fake domains in user links. 

* Bug in user page in title. 

* Bug in incorrect admin link print. 

* Workflow. 

* Release bug. 

* Exception in number of days. 

* Add delay before finishing the request in applying actions. 

* Showing toast on pwa. 

* Video and toast. 

* Bug not updating users. 

* Typo. 

* Bug in db domain. 

* First setup. 

* Bug in init db. 

* Not showing home title in homepage. 

* Update translations. 

* Disable some protocols in clash. 

* Clash bugs. 

* Add port. 

* Bug in model. 

* Cipher. 

* Configs in clash. 

* Clash links. 

* Clash proxies. 

* Ptls bug. 

* Clash proxies. 

* H2 links. 

* Linkmaker. 

* Import. 

* Add vless xtls. 

* H2 not showing. 

* Show v2ray configs if enabled. 

* Db. 

* Ports. 

* Typo. 

* Alpn. 

* Bug in clash. 

* Bug in ws. 

* Domain bug. 

* Clash bug. 

* Revert using api for disconnect connect users. 

* Domain. 

* Typo. 

* Python bug. 

* Typo. 

* Not showing apply config dialog. 

* Delete h1 in transport. 

* Sublink for ios. 

* Vmess host not in link. 

#### Other

* Fix bug. 

* Add hiddify. 

* Remove dynaconf. 

* Update and remove extra libs. 

* Refactor. 

* Update. 

* Add clean ip support. 

* Disbale main workflow. 

* New. 

* Test. 

* Test release. 

* Fix compile error. 

* Check. 

* Fix big. 

* New test. 

* Fix. 

* Fix. 

* Fix. 

* Fix. 

* Test. 

* Set to python 3.10. 

* Add version. 

* Pypi to hiddify-config. 

* Update. 

* Test. 

* Fix support page. 

* Remove extra log. 

* Fix xtls alpn. 



## 1.6.8 (2023-03-09)

#### Fix

* Bug in clash config. 



## 1.6.7 (2023-03-08)

#### New

* Revert back to old clash config. 

#### Changes

* Update clash configs. 

#### Fix

* Bug in clash profiles. 



## 1.6.6 (2023-03-08)

#### Fix

* Restore backup when no start days. 



## 1.6.5 (2023-03-08)

#### New

* Add backup by cli. 

#### Changes

* Better backup file name format. 

#### Fix

* Change subscription link to trojan for better compatibility. 

* When package days is not defined. 



## 1.6.0 (2023-03-08)

#### New

* New telegram bot features. 

* Update bot features. 

#### Fix

* Telegrambot. 

#### Other

* Merge branch 'main' of github.com:hiddify/HiddifyPanel. 

* Merge pull request #9 from ehsanmqn/main. 
  _Cleaning some codes based on PEP8 and adding description to the vital classes_

* Merge branch 'main' into main. 

* Short descriptions added to the classes and functions within the user.py file. 

* Imports rearranged. 

* Useless imports removed. 

* File reorganized according to PEP8 principles for increasing code readability. 

* File reorganized according to PEP8 principles for increasing code readability. 

* Merge remote-tracking branch 'refs/remotes/origin/main' 

* File reorganized according to PEP8 principles for increasing code readability. 

* File reorganized according to PEP8 principles for increasing code readability. 



## 1.5.3 (2023-03-08)

#### Changes

* Add username to bot. 

#### Fix

* Bug in v2rayng link. 

* Bug in launching app if telegram has error. 



## 1.5.2 (2023-03-08)

#### Fix

* Bug in v2ray. 



## 1.5.1 (2023-03-08)

#### Fix

* Bug in editing page. 



## 1.5.0 (2023-03-08)

#### New

* Make proxy path to be changed. 

* Add multi remove. 

* New path format. 

* Better displaying usage in ios. 

* Change proxy_path for more security. 

* Add random path for vmess,vless,v2ray,trojan. 

#### Changes

* Change base proxy path to too advanced. 

* V2ray to ss. 

#### Fix

* Bug in import users. 

* Bug in editing users. 

* Domain not showing in the domain section. 

* Red color in user page. 

* Theme bug. 

* Vmess grpc link. 

* Usage. 

* Bug in grpc vmess. 

* Wrong user usage update. 

* Remove old user when change uuid. 

* Bug not disconnecting a user on delete. 

* Add_path. 

* More stable green cadre. 



## 1.4.2 (2023-03-07)

#### New

* Add /admin without / as correct path. 

#### Fix

* Bug in telegrambot. 



## 1.4.1 (2023-03-07)

#### Fix

* Bug in add new user. 



## 1.4.0 (2023-03-07)

#### New

* Show usage in user panel. 

#### Fix

* Add some log into bot. 

* Telegram bot. 

#### Other

* Update translation. 

* Merge pull request #7 from ehsanmqn/main. 
  _Updating the telegram bot commands_

* Merge branch 'main' into main. 

* Text updated. 

* Text updated. 

* Text updated. 

* Text updated. 

* Docs added to telegram commands. 

* Docs added to telegram commands. 

* Doc added to prepare_welcome_message. 

* Doc added to prepare_welcome_message. 

* Doc added to prepare_help_message. 

* Doc added to prepare_me_info. 

* Start command changed to hello. 

* Imports rearranged. 

* Command_me completed. 

* Command_me updated. 

* Command_start updated. 

* Command_start updated. 

* Prepare_me_info added. 

* Function name updated to command_info. 

* Function name updated to command_start. 

* Command_help added. 

* Information bot updated. 

* Information bot added. 

* Information bot added. 

* Useless imports removed. 

* Welcome message updated. 

* Welcome message updated. 

* Imports reorganized. 

* Text formatted according to PEP8. 

* Useless imports removed. 

* Useless lines removed from the update_usage_callback function. 

* Useless lines removed from the get_usage_msg function. 

* Useless lines removed from the send_welcome function. 

* File reformatted according to PEP8. 

* File reorganized. 

* File reorganized. 

* Useless commented get function removed. 

* Useless imports removed. 

* Import moved to top. 

* Import moved to top. 

* Useless comment removed. 

* File reformatted according to PEP8. 

* Imports reorganized for better code review. 

* Useless commented import removed. 

* .vscode removed from the project. 



## 1.3.0 (2023-03-07)

#### New

* Add reset user's package (usage and days) 

#### Changes

* Better displaying how to change user mode. 



## 1.2.2 (2023-03-07)

#### New

* Change the default link. 



## 1.2.1 (2023-03-07)

#### New

* New favicon. 



## 1.2.0 (2023-03-07)

#### New

* Add hour in the fakeip. 

* Add fetch date as ip in the subscription link. 

* Add v2rayng as supported link for android. 

* Hide decoy port setting :D. 

* Speedup user add or remove using renewed api. 

* Speedup xray fire user. 

* Add expire days in subscription link. 

* Add usage to subscription link. 

* Add disable to users. 

* Add telegram bot command for create multiple account. 

* Users expire time will now starts from their first connection. 

#### Changes

* Add all proxies again in the clash config. 

#### Fix

* Add space in subscription link. 

* Log in xray api. 

* Bug in xray api. 

* Bug in update usage. 

* Bug in calculating active users. 

* Bug in cli. 

* Not showing reset time. 

* Bug in date. 

* Name in clash. 

#### Other

* Fix exception in remove. 

* Add log in xray api. 

* Update xray log. 



## 1.1.2 (2023-03-05)

#### New

* New icon. 

* Change backend uwsgi. 



## 1.1.1 (2023-03-05)

#### Fix

* Bug in update when one usage used out usage. 



## 1.1.0 (2023-03-05)

#### New

* Enable tuic and shadowtls for public. 

* Enable tuic for all. 

* Add tuic !!! The fastest protocol with lowest latency. 

* Add alias for telegram. 

* Add support for shadowtls. 

* Make proxies selectable for each domain. 

* Show selectable proxies first. 

* Remove all proxies. 

* Better organization of proxies in clash. 

* Add a profile for each domain in clash configs. 

* Show apply config on changing domain only when needed. 

* Add description for adding alias. 

* Add custom name for domain (alias) 

* Allow users to select proxies from only one domain in clash. 

* Add sequential, loadbalance and auto as an option to select specific domain in clash. 

* Add load balance in clash rules. 

* Telegram bot, We need contributors in this part. 

* Add simple telegram bot. 

#### Changes

* Add demo bot request. 

* Improve translations. 

#### Fix

* Tuic will not shown in normal clash. 

* Change tuic params. 

* Bug in clash config for tuic. 

* Clash config with tuic. 

* Showing tuic only for direct domains. 

* Tuic in proxies. 

* Bug in clash profile. 

* Not displaying green box in update. 

* Db version. 

* Add consistency in changing dbversion. 

* Bug in enabling tuic and shadowtls. 

* Telegram link bug. 

* Hide release commits. 

* Alias name in clash config. 

* Bug in showing a specific domain. 

* Bug in clash config. 

* Bug in usage reset time. 

* Bug in showing last day. 

#### Other

* Fix cert error in tuic. 

* Change release log format. 



## 1.0.0 (2023-02-28)

#### New

* Add default parent domain. 

#### Fix

* Show success message only on end. 

#### Other

* Add utls to be configured. 

* Show domain change window after quick setup. 



## 0.9.111 (2023-02-28)

#### Other

* Add dev branch. 



## 0.9.110 (2023-02-28)

#### Fix

* Restore error. 



## 0.9.109 (2023-02-28)

#### Fix

* Adding unique id for old installations. 



## 0.9.108 (2023-02-28)

#### Fix

* Bug in quick setup. 

* Bug in quick setup. 



## 0.9.107 (2023-02-28)

#### Fix

* Bug in restore domain. 



## 0.9.106 (2023-02-28)

#### Fix

* Bug in child. 



## 0.9.105 (2023-02-28)

#### Fix

* Bug in child_ip. 



## 0.9.104 (2023-02-28)

#### Fix

* Bug in admin layout. 



## 0.9.103 (2023-02-28)

#### New

* Add actions in parent. 



## 0.9.102 (2023-02-28)

#### Fix

* Bug in setting child. 



## 0.9.101 (2023-02-28)

#### New

* Add api. 



## 0.9.100 (2023-02-28)

#### Other

* Change default fingerprint to andorid. 



## 0.9.99 (2023-02-28)

#### New

* Add telegram_bot_token. 

* Better verify domain. 



## 0.9.98 (2023-02-27)

#### Fix

* Relase message bug. 

* Bug in release message. 

* Version error. 

#### Other

* Update. 

* Update. 



## 0.9.96 (2023-02-27)

#### Other

* Update relative date to days if less than 2 months. 



## 0.9.95 (2023-02-27)

#### Fix

* Bug in user panel. 

#### Other

* Update. 



## 0.9.94 (2023-02-27)

#### Other

* Update. 

* Update stash and shadowlink. 



## 0.9.93 (2023-02-27)

#### Other

* Fix bug when user max usage is zero. 

* Add parent_domains to cli. 



## 0.9.92 (2023-02-27)

#### Other

* Fix expirydate issue. 



## 0.9.91 (2023-02-26)

#### Other

* Fix bool config. 



## 0.9.90 (2023-02-26)

#### Other

* Fix last online. 



## 0.9.89 (2023-02-26)

#### Other

* Fix. 

* Fix bug. 



## 0.9.88 (2023-02-26)

#### Other

* Add pyyaml. 



## 0.9.87 (2023-02-26)

#### Other

* Remove update db notif. 



## 0.9.86 (2023-02-26)

#### Other

* Fix auto update usage. 

* Update db on init. 



## 0.9.85 (2023-02-26)

#### Other

* Fix update usage. 



## 0.9.84 (2023-02-26)

#### Other

* Fix null bug. 



## 0.9.83 (2023-02-26)

#### Other

* Update. 

* Add chart for online user. 

* Add online users. 



## 0.9.82 (2023-02-26)

#### Other

* Fix bad bug. 



## 0.9.81 (2023-02-26)

#### Other

* Add tun mode in clash proxies. 

* Not exist domain. 



## 0.9.80 (2023-02-26)

#### Other

* Update. 

* Fix bug in import users. 

* Update centeral panel layoutt. 



## 0.9.79 (2023-02-26)

#### Other

* Fix. 



## 0.9.78 (2023-02-26)

#### Other

* Fix. 

* Update. 



## 0.9.77 (2023-02-26)

#### Other

* Update. 



## 0.9.76 (2023-02-26)

#### Other

* Fix change lang issue. 



## 0.9.75 (2023-02-26)

#### Other

* Fix backup. 

* Update. 



## 0.9.74 (2023-02-26)

#### Other

* Fix. 

* Update. 



## 0.9.73 (2023-02-26)

#### Other

* Fix. 



## 0.9.72 (2023-02-26)

#### Other

* Fix. 



## 0.9.71 (2023-02-26)

#### Other

* Fix update panel. 



## 0.9.70 (2023-02-26)

#### Other

* Update. 

* Update. 

* Fix updateusage. 

* Fix. 

* Update panel. 

* Fix. 

* Fix child. 

* Fix db. 

* Add config cli. 

* Fix. 

* Fix domains. 

* Update. 

* Updaet. 

* Add unique id. 

* Update. 

* Update. 

* Update. 

* Update. 

* Add json. 

* Update. 

* Fix. 

* Update. 

* Update. 

* Add set config from cli. 

* Fix all configs. 

* Add parent panel. 



## 0.9.66 (2023-02-25)

#### Other

* Fix multi link. 

* Merge branch 'main' of github.com:hiddify/HiddifyPanel. 

* Update README.md. 



## 0.9.65 (2023-02-24)

#### Other

* Fix restore and backup of domains. 



## 0.9.64 (2023-02-23)

#### Other

* Fix backup. 



## 0.9.63 (2023-02-23)

#### Other

* Fix backup. 



## 0.9.62 (2023-02-22)

#### Other

* Fix loop. 



## 0.9.61 (2023-02-22)

#### Other

* Fix. 



## 0.9.60 (2023-02-22)

#### Other

* Add hiddify desktop. 

* Add ability to change proxy path. 

* Add restore settings enable disable. 

* Add more info about relay and fake. 



## 0.9.59 (2023-02-22)

#### Other

* Update. 

* Update. 

* Update. 



## 0.9.58 (2023-02-22)

#### Other

* Add autopep8. 

* Adding domain specific configuration. 

* Add reset after 30 days. 

* Add version to home. 



## 0.9.57 (2023-02-17)

#### Other

* FIX. 

* Change  admin secret to lower case. 

* Update ios. 



## 0.9.56 (2023-02-16)

#### Other

* Add ios. 



## 0.9.55 (2023-02-16)

#### Other

* Fix stash link in ios. 



## 0.9.54 (2023-02-16)

#### Other

* Fix support box in mobile. 



## 0.9.53 (2023-02-16)

#### Other

* Add version in menu. 



## 0.9.52 (2023-02-16)

#### Other

* Add version to sidebar. 



## 0.9.51 (2023-02-16)

#### Other

* Fix layout. 



## 0.9.50 (2023-02-16)

#### Other

* Update. 

* Notify domain change on backup. 



## 0.9.49 (2023-02-16)

#### Other

* Update. 



## 0.9.47 (2023-02-16)

#### Other

* Fix click. 



## 0.9.46 (2023-02-16)

#### Other

* Fix error. 



## 0.9.45 (2023-02-16)

#### Other

* Update. 

* Fix not showing date in firefox. 



## 0.9.44 (2023-02-16)

#### Other

* Update. 

* Fix error in change proxy apply. 



## 0.9.43 (2023-02-16)

#### Other

* Remove some dependencies. 



## 0.9.42 (2023-02-16)

#### Other

* Update. 



## 0.9.41 (2023-02-16)

#### Other

* Update. 



## 0.9.40 (2023-02-15)

#### Other

* Fix exception. 



## 0.9.39 (2023-02-15)

#### Other

* Add domain name to clash proxy. 

* Allow ipv6. 

* Update. 

* Fix invalid domain names for decoy website. 



## 0.9.38 (2023-02-15)

#### Other

* Add hiddify proxy v0.11. 



## 0.9.37 (2023-02-15)

#### Other

* Update. 

* Update. 



## 0.9.35 (2023-02-15)

#### Other

* Add version. 

* Add version in panel. 



## 0.9.33 (2023-02-15)

#### Other

* Add hiddify android v 0.10. 

* Add global client fingerprint. 

* Fix ipv6. 



## 0.9.31 (2023-02-15)

#### Other

* Fix full install everytime. 



## 0.9.30 (2023-02-15)

#### Other

* Fix represntation of fake in user page. 



## 0.9.29 (2023-02-15)

#### Other

* Add fake domain. 



## 0.9.28 (2023-02-15)

#### Other

* Add fake domain. 



## 0.9.27 (2023-02-15)

#### Other

* Update. 



## 0.9.26 (2023-02-14)

#### Other

* Update. 



## 0.9.25 (2023-02-14)

#### Other

* Update. 



## 0.9.22 (2023-02-14)

#### Other

* Fix. 



## 0.9.21 (2023-02-14)

#### Other

* Remove direct links in CDN. 



## 0.9.20 (2023-02-14)

#### Other

* Fix direct domain db. 



## 0.9.19 (2023-02-14)

#### Other

* Add ipv6 connections. 



## 0.9.18 (2023-02-14)

#### Other

* Update multi domain. 



## 0.9.17 (2023-02-14)

#### Other

* Update. 



## 0.9.15 (2023-02-14)

#### Other

* Add multi link. 



## 0.9.14 (2023-02-14)

#### Other

* Update. 



## 0.9.13 (2023-02-14)

#### Other

* Fix. 



## 0.9.12 (2023-02-13)

#### Other

* Add fingerprint in share link. 



## 0.9.11 (2023-02-13)

#### Other

* Remove need for apply for adding a user. 

* Update. 



## 0.9.10 (2023-02-10)

#### Other

* Add grpc direct. 

* Add relay mode. 



## 0.9.9 (2023-02-09)

#### Other

* Update quick setup. 

* Update. 

* Update. 



## 0.9.8 (2023-02-09)

#### Other

* Update. 



## 0.9.7 (2023-02-09)

#### Other

* Fix translation. 



## 0.9.6 (2023-02-09)

#### Other

* Add specified ip for cdn hosts. 

* Add forced ip. 



## 0.9.5 (2023-02-09)

#### Other

* Remove. 



## 0.9.4 (2023-02-09)

#### Other

* Update. 



## 0.9.3 (2023-02-09)

#### Other

* Update. 

* Add fingerprint. 

* Add fingerprint. 



## 0.9.2 (2023-02-09)

#### Other

* Fix xtls vision. 

* Remove trojan and add vless. 

* Remove xtls direct. 



## 0.9.1 (2023-02-09)

#### Other

* Fix layout. 

* Update. 

* Update link. 

* Update. 

* Update. 

* Update. 

* Update. 

* Update. 

* Add link from domain to admin page. 

* Update ui. 

* Ram update. 

* Update. 

* Update. 

* Update. 

* Update. 

* Update. 

* Update. 

* Update. 

* Update. 

* Update ux and ui in admin. 

* Update. 

* Fix emergency access. 

* Fix. 

* Organizing db. 

* Fix error csrf. 

* Fix. 

* Update. 

* Remove verification. 

* Fix setting admin. 

* Fix. 

* Update. 

* Update. 

* Fix caps domain. 

* Fix v2ray. 

* Remove csrf. 

* Fix not creating same uuid in restore. 

* Fix alpn. 

* Remove alpn for h2 in links. 

* Fix faketls. 

* Update. 

* Update. 

* Update. 

* Update link_maker.py. 

* Update link_maker.py. 

* Update. 

* Fix. 

* Update icon. 

* Update usage. 

* Add domain to infoname. 

* Fix bug. 

* Fix domain fronting. 

* Showing alert before leaving apply settings page. 

* Update. 

* Lang update. 

* Update. 

* Fix. 

* Fix. 

* Fix fake. 

* Update. 

* Fix bug. 

* Add temporary link. 

* Fix bug. 

* Fix. 

* Update. 

* Update. 

* Add an option to select between monthly and total. 

* Update translation. 

* Add some configs. 

* Update. 

* Update. 

* Update translation. 

* Add backup and restore. 

* Fix support link. 

* Fix admin link. 

* Update. 

* Fix bug in domain. 

* Update. 

* Fix ip removed. 

* Update lang. 

* Validate domain. 

* Fix domian. 

* Add user error message. 

* Fix bug. 

* Update. 

* Fix. 

* Add first setup. 

* Fix init bug. 

* Update. 

* Update. 



## 0.9.0 (2023-02-04)

#### Other

* Update translations. 

* Update. 

* Add donation link. 

* Add apply config for users. 

* Update. 

* Add branding link. 

* Update. 

* Update ui. 

* Full. 

* Update. 

* Add full install option. 

* Update. 

* Update. 

* Update telegram lib. 

* Quicksetup lang. 

* Add admin language. 

* Update. 

* Update admin lang. 

* Fix delete user error. 

* Fix. 

* Update. 

* Fix update db version. 

* Update db. 

* Add log for initdb. 

* Update. 

* Fixed. 

* Fix user. 

* Update translations. 

* Update. 

* Charts info. 

* Update. 

* Update. 

* Add telegram lib. 

* Fix float. 

* Fix sqlalchemy. 

* Update. 

* Remove some logs. 

* Update. 

* Add temporary rule for firewall to access. 

* Random port. 

* Fix not reset the usage. 

* Add icon, add temp port update message. 

* Update remove incomplete configs. 

* Small fix. 

* Fix user remove error and more checkings. 

* Fix link. 

* Fix link. 

* Add api. 

* Fix usage shown. 

* Update. 

* Add log finish message. 

* Add default user link info message for quick setup. 



## 0.8.6 (2023-02-03)

#### Other

* Update. 



## 0.8.5 (2023-02-03)

#### Other

* Fix grpc link. 

* Fix normal clash link. 

* Fix bug in versioning. 



## 0.8.4 (2023-02-03)

#### Other

* Fix bugs. 



## 0.8.3 (2023-02-03)

#### Other

* Fix uuid. 



## 0.8.2 (2023-02-03)

#### Other

* Fix vmess links. 

* Fix grpc. 

* Fix ios links. 

* Fix bug in telegram and not showing all emails. 



## 0.8.1 (2023-02-02)

#### Other

* Fix bug in time. 



## 0.8.0 (2023-02-02)

#### Other

* Update. 

* Update. 

* Update. 

* Update ui. 

* Update style. 

* Update style. 

* Update. 

* Update http-opts. 

* Fix. 

* Update link maker. 

* Fix port bug. 

* Update. 

* Fix bug. 

* Remove vless and xtls and shadowtls for normal clash. 



## 0.7.0 (2023-02-02)

#### Other

* Update. 

* Update clashlinks. 

* Fix update usage. 



## 0.6.0 (2023-02-02)

#### Other

* Update. 

* New translations. 

* Fix. 

* Fix bug. 



## 0.5.0 (2023-02-02)

#### Other

* Update translation. 

* Add auto update translations. 

* Fix import. 

* Add mo files. 

* Trying to fix translation issues. 

* Update translations. 

* Update. 

* Add translations. 

* Update. 

* Add link. 

* Add chinese lang. 

* Add auto translate. 

* Fix. 

* Fix translations. 

* Remove changing proxy path. 

* Add success notification to domain. 

* Remove category from config. 

* Update. 

* Update. 

* Fix decoy site to domain. 

* Update order. 

* Update. 

* Reorgnizing. 

* Fix cli bug. 

* Update. 

* Update. 



## 0.4.0 (2023-02-01)

#### Other

* Update FUNDING.yml. 

* Update. 

* Add selectable proxies. 

* Selectable proxy. 

* Update. 

* Latest update. 

* Update. 

* Adding tuic, shadowtls, ssr, ui improvment. 

* Update user ui. 

* Update. 



## 0.3.0 (2023-01-22)

#### Other

* Include static files. 

* Update cli. 

* Fix prob. 



## 0.0.2 (2023-01-22)

#### Other

* Update. 

* Update. 

* Update and reset automatically the usage. 



## 0.0.1 (2023-01-21)

#### Other

* Remove windows and mac. 

* Update. 

* Add update storage. 

* First working version. 

* Create default db. 

* Update to bootstrap 5. 

* ✅ Ready to clone and code. 

* Initial commit. 



