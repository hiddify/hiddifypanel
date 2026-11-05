/**
 * Ready-made designs for the support box (Full mode's template gallery). Only tags and CSS the panel keeps when it saves
 * the text (hutils/user_html): inline styles, no positioning, no url(). Each one is short, so it fits the setting's limit.
 */

/** The gallery's sections, in this order. */
export const TEMPLATE_GROUPS = ['contact', 'news', 'sales', 'guide'] as const
export type TemplateGroup = (typeof TEMPLATE_GROUPS)[number]

export interface SupportTemplate {
  id: string
  group: TemplateGroup
  html: string
}

const BTN = 'display: inline-block; padding: 8px 16px; border-radius: 999px; font-weight: 600; text-decoration: none'

export const TEMPLATES: SupportTemplate[] = [
  {
    id: 'hero',
    group: 'contact',
    html: `<div style="padding: 16px; border-radius: 16px; background: linear-gradient(135deg, #4f46e5, #06b6d4); color: #ffffff; text-align: center"><p style="margin: 0 0 4px; font-size: 18px; font-weight: 700">💬 24/7 Support</p><p style="margin: 0 0 12px; opacity: 0.9">Questions? We answer within minutes.</p><a href="https://t.me/" target="_blank" style="${BTN}; background: #ffffff; color: #4f46e5">Telegram</a></div>`,
  },
  {
    id: 'contacts',
    group: 'contact',
    html: `<div style="display: flex; flex-direction: column; gap: 8px"><a href="https://t.me/" target="_blank" style="display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 12px; background: #ffffff; color: #212529; text-decoration: none; border: 1px solid #dee2e6">✈️ <b>Telegram</b><span style="margin-inline-start: auto; color: #455fe9">@support</span></a><a href="mailto:support@example.com" style="display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 12px; background: #ffffff; color: #212529; text-decoration: none; border: 1px solid #dee2e6">✉️ <b>Email</b><span style="margin-inline-start: auto; color: #455fe9">support@example.com</span></a><a href="tel:+10000000000" style="display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 12px; background: #ffffff; color: #212529; text-decoration: none; border: 1px solid #dee2e6">📞 <b>Phone</b><span style="margin-inline-start: auto; color: #455fe9">+1 000 000 0000</span></a></div>`,
  },
  {
    id: 'announcement',
    group: 'news',
    html: `<div style="padding: 12px 14px; border-radius: 12px; background: #fff9db; border: 1px solid #ffe066; color: #5c4400"><p style="margin: 0 0 4px; font-weight: 700">📢 Announcement</p><p style="margin: 0">New servers are online. Update your subscription in the app to use them.</p></div>`,
  },
  {
    id: 'alerts',
    group: 'news',
    html: `<div style="display: flex; flex-direction: column; gap: 8px"><div style="padding: 10px 12px; border-radius: 10px; background: #ebfbee; border-inline-start: 4px solid #2f9e44; color: #1b5e2b">✅ All servers are working normally.</div><div style="padding: 10px 12px; border-radius: 10px; background: #e7f5ff; border-inline-start: 4px solid #1971c2; color: #0b4a7d">ℹ️ Scheduled maintenance on Friday, 02:00–03:00.</div><div style="padding: 10px 12px; border-radius: 10px; background: #fff4e6; border-inline-start: 4px solid #f76707; color: #7a3300">⚠️ Renew before your plan ends to keep your settings.</div></div>`,
  },
  {
    id: 'faq',
    group: 'guide',
    html: `<div style="display: flex; flex-direction: column; gap: 6px"><details style="padding: 10px 12px; border-radius: 10px; background: #ffffff; border: 1px solid #dee2e6"><summary style="font-weight: 600">How do I connect?</summary><p style="margin: 8px 0 0">Install the app, then import your subscription link.</p></details><details style="padding: 10px 12px; border-radius: 10px; background: #ffffff; border: 1px solid #dee2e6"><summary style="font-weight: 600">It does not connect, what now?</summary><p style="margin: 8px 0 0">Update the subscription, switch to another config, or message support.</p></details></div>`,
  },
  {
    id: 'columns',
    group: 'contact',
    html: `<div style="display: flex; gap: 8px"><div style="flex: 1; padding: 12px; border-radius: 12px; background: #ffffff; border: 1px solid #dee2e6; text-align: center"><p style="margin: 0 0 4px; font-size: 22px">✈️</p><p style="margin: 0 0 8px; font-weight: 600">Telegram</p><a href="https://t.me/" target="_blank" style="color: #455fe9; text-decoration: underline">Open</a></div><div style="flex: 1; padding: 12px; border-radius: 12px; background: #ffffff; border: 1px solid #dee2e6; text-align: center"><p style="margin: 0 0 4px; font-size: 22px">✉️</p><p style="margin: 0 0 8px; font-weight: 600">Email</p><a href="mailto:support@example.com" style="color: #455fe9; text-decoration: underline">Write</a></div></div>`,
  },
  {
    id: 'plan',
    group: 'sales',
    html: `<div style="padding: 16px; border-radius: 16px; background: #ffffff; border: 2px solid #455fe9; box-shadow: 0 8px 24px -12px rgba(69, 95, 233, 0.5)"><p style="margin: 0; color: #455fe9; font-weight: 700">⭐ Premium</p><p style="margin: 4px 0 8px; font-size: 26px; font-weight: 800; color: #212529">$5 <span style="font-size: 14px; font-weight: 400; color: #868e96">/ month</span></p><ul style="list-style: none; margin: 0 0 12px; padding: 0; line-height: 1.9"><li>✔️ Unlimited traffic</li><li>✔️ 3 devices</li><li>✔️ Priority support</li></ul><a href="https://t.me/" target="_blank" style="${BTN}; background: #455fe9; color: #ffffff">Renew now</a></div>`,
  },
  {
    id: 'hours',
    group: 'contact',
    html: `<p style="margin: 0 0 6px; font-weight: 700">🕒 Support hours</p><table style="width: 100%; border-collapse: collapse; background: #ffffff; border-radius: 10px"><tbody><tr><td style="padding: 6px 10px; border-bottom: 1px solid #e9ecef">Sat – Wed</td><td style="padding: 6px 10px; border-bottom: 1px solid #e9ecef; text-align: end">09:00 – 23:00</td></tr><tr><td style="padding: 6px 10px; border-bottom: 1px solid #e9ecef">Thursday</td><td style="padding: 6px 10px; border-bottom: 1px solid #e9ecef; text-align: end">09:00 – 18:00</td></tr><tr><td style="padding: 6px 10px">Friday</td><td style="padding: 6px 10px; text-align: end; color: #e03131">Closed</td></tr></tbody></table>`,
  },
  {
    id: 'social',
    group: 'contact',
    html: `<p style="margin: 0 0 8px; text-align: center; font-weight: 600">Follow us</p><div style="display: flex; flex-wrap: wrap; gap: 6px; justify-content: center"><a href="https://t.me/" target="_blank" style="${BTN}; background: #229ed9; color: #ffffff">Telegram</a><a href="https://instagram.com/" target="_blank" style="${BTN}; background: #d6336c; color: #ffffff">Instagram</a><a href="https://x.com/" target="_blank" style="${BTN}; background: #212529; color: #ffffff">X</a><a href="https://youtube.com/" target="_blank" style="${BTN}; background: #e03131; color: #ffffff">YouTube</a></div>`,
  },
  {
    id: 'steps',
    group: 'guide',
    html: `<p style="margin: 0 0 8px; font-weight: 700">🚀 Get started in 3 steps</p><ol style="list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px"><li style="display: flex; gap: 10px; align-items: center"><span style="display: inline-block; width: 24px; height: 24px; border-radius: 999px; background: #455fe9; color: #ffffff; text-align: center; line-height: 24px; font-weight: 700">1</span>Install the Hiddify app</li><li style="display: flex; gap: 10px; align-items: center"><span style="display: inline-block; width: 24px; height: 24px; border-radius: 999px; background: #455fe9; color: #ffffff; text-align: center; line-height: 24px; font-weight: 700">2</span>Import your subscription link</li><li style="display: flex; gap: 10px; align-items: center"><span style="display: inline-block; width: 24px; height: 24px; border-radius: 999px; background: #455fe9; color: #ffffff; text-align: center; line-height: 24px; font-weight: 700">3</span>Tap Connect</li></ol>`,
  },
  // ---- more designs ----
  {
    id: 'darkCard',
    group: 'contact',
    html: `<div style="padding: 20px; border-radius: 18px; background: linear-gradient(160deg, #1e1b4b, #312e81 60%, #4338ca); color: #e0e7ff; box-shadow: 0 12px 30px -14px rgba(49, 46, 129, 0.8)"><p style="margin: 0; font-size: 12px; letter-spacing: 0.12em; text-transform: uppercase; color: #a5b4fc">Need help?</p><p style="margin: 6px 0 14px; font-size: 20px; font-weight: 800; color: #ffffff">We are one message away</p><div style="display: flex; flex-wrap: wrap; gap: 8px"><a href="https://t.me/" target="_blank" style="${BTN}; background: #ffffff; color: #312e81">✈️ Telegram</a><a href="mailto:support@example.com" style="${BTN}; background: rgba(255, 255, 255, 0.12); color: #ffffff; border: 1px solid rgba(255, 255, 255, 0.3)">✉️ Email</a></div></div>`,
  },
  {
    id: 'minimal',
    group: 'contact',
    html: `<div style="text-align: center; padding: 8px 0"><p style="margin: 0 0 4px; font-size: 16px; font-weight: 700">Hiddify Support</p><p style="margin: 0 0 10px; color: #868e96; font-size: 13px">Fast, private and always here for you</p><hr style="width: 48px; margin: 0 auto 10px; border: 0; border-top: 2px solid #455fe9"><p style="margin: 0; font-size: 13px"><a href="https://t.me/" target="_blank" style="color: #455fe9; text-decoration: none">Telegram</a> · <a href="mailto:support@example.com" style="color: #455fe9; text-decoration: none">Email</a> · <a href="https://example.com/" target="_blank" style="color: #455fe9; text-decoration: none">Website</a></p></div>`,
  },
  {
    id: 'persian',
    group: 'contact',
    html: `<div dir="rtl" style="padding: 16px; border-radius: 16px; background: linear-gradient(135deg, #0ca678, #1098ad); color: #ffffff; text-align: right"><p style="margin: 0 0 4px; font-size: 18px; font-weight: 800">🎧 پشتیبانی ۲۴ ساعته</p><p style="margin: 0 0 12px; opacity: 0.92">سؤالی دارید؟ در کمتر از چند دقیقه پاسخ می‌دهیم.</p><div style="display: flex; flex-wrap: wrap; gap: 8px"><a href="https://t.me/" target="_blank" style="${BTN}; background: #ffffff; color: #087f5b">پیام در تلگرام</a><a href="tel:+10000000000" style="${BTN}; background: rgba(255, 255, 255, 0.15); color: #ffffff; border: 1px solid rgba(255, 255, 255, 0.4)">تماس تلفنی</a></div></div>`,
  },
  {
    id: 'serverStatus',
    group: 'news',
    html: `<div style="padding: 14px; border-radius: 14px; background: #ffffff; border: 1px solid #e9ecef; box-shadow: 0 6px 18px -12px rgba(0, 0, 0, 0.3)"><p style="margin: 0 0 10px; font-weight: 700">📡 Server status</p><div style="display: grid; grid-template-columns: 1fr auto; gap: 8px 12px; font-size: 14px"><span>🟢 Germany</span><span style="color: #2f9e44; font-weight: 600">Online · 42 ms</span><span>🟢 Netherlands</span><span style="color: #2f9e44; font-weight: 600">Online · 55 ms</span><span>🟡 Finland</span><span style="color: #e67700; font-weight: 600">Busy · 120 ms</span><span>🔴 Turkey</span><span style="color: #e03131; font-weight: 600">Maintenance</span></div></div>`,
  },
  {
    id: 'changelog',
    group: 'news',
    html: `<p style="margin: 0 0 10px; font-weight: 800; font-size: 16px">✨ What's new</p><div style="display: flex; flex-direction: column; gap: 10px"><div style="padding-inline-start: 12px; border-inline-start: 3px solid #7950f2"><p style="margin: 0; font-size: 12px; color: #7950f2; font-weight: 700">This week</p><p style="margin: 2px 0 0">Two new locations: Canada and Japan.</p></div><div style="padding-inline-start: 12px; border-inline-start: 3px solid #adb5bd"><p style="margin: 0; font-size: 12px; color: #868e96; font-weight: 700">Last month</p><p style="margin: 2px 0 0">Faster connections on mobile networks.</p></div><div style="padding-inline-start: 12px; border-inline-start: 3px solid #adb5bd"><p style="margin: 0; font-size: 12px; color: #868e96; font-weight: 700">Earlier</p><p style="margin: 2px 0 0">Support for the new Hiddify app.</p></div></div>`,
  },
  {
    id: 'renew',
    group: 'news',
    html: `<div style="display: flex; align-items: center; gap: 12px; padding: 14px; border-radius: 14px; background: linear-gradient(135deg, #fff3bf, #ffe8cc); border: 1px solid #ffd8a8"><span style="font-size: 30px">⏳</span><div style="flex: 1"><p style="margin: 0; font-weight: 800; color: #862e00">Your plan ends soon</p><p style="margin: 2px 0 0; font-size: 13px; color: #a34700">Renew now and keep every setting.</p></div><a href="https://t.me/" target="_blank" style="${BTN}; background: #e8590c; color: #ffffff">Renew</a></div>`,
  },
  {
    id: 'plans',
    group: 'sales',
    html: `<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px"><div style="padding: 14px; border-radius: 14px; background: #ffffff; border: 1px solid #dee2e6; text-align: center"><p style="margin: 0; font-weight: 700; color: #495057">Basic</p><p style="margin: 6px 0; font-size: 24px; font-weight: 800">$3</p><p style="margin: 0 0 10px; font-size: 13px; color: #868e96">50 GB · 1 device</p><a href="https://t.me/" target="_blank" style="${BTN}; background: #f1f3f5; color: #212529">Choose</a></div><div style="padding: 14px; border-radius: 14px; background: linear-gradient(160deg, #7048e8, #455fe9); color: #ffffff; text-align: center; box-shadow: 0 10px 24px -12px #5f3dc4"><p style="margin: 0; font-weight: 700">Pro 🔥</p><p style="margin: 6px 0; font-size: 24px; font-weight: 800">$7</p><p style="margin: 0 0 10px; font-size: 13px; opacity: 0.85">Unlimited · 5 devices</p><a href="https://t.me/" target="_blank" style="${BTN}; background: #ffffff; color: #5f3dc4">Choose</a></div></div>`,
  },
  {
    id: 'offer',
    group: 'sales',
    html: `<div style="padding: 18px; border-radius: 18px; background: linear-gradient(135deg, #f03e3e, #d6336c 50%, #ae3ec9); color: #ffffff; text-align: center"><p style="margin: 0; font-size: 13px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; opacity: 0.9">Limited offer</p><p style="margin: 4px 0; font-size: 34px; font-weight: 900">30% OFF</p><p style="margin: 0 0 12px; opacity: 0.9">On every yearly plan, this week only.</p><p style="display: inline-block; margin: 0; padding: 6px 14px; border: 2px dashed rgba(255, 255, 255, 0.8); border-radius: 10px; font-weight: 800; letter-spacing: 0.12em">HIDDIFY30</p></div>`,
  },
  {
    id: 'referral',
    group: 'sales',
    html: `<div style="display: flex; align-items: center; gap: 14px; padding: 16px; border-radius: 16px; background: #f3f0ff; border: 1px solid #d0bfff"><span style="display: inline-block; width: 48px; height: 48px; flex: none; border-radius: 14px; background: linear-gradient(135deg, #845ef7, #5f3dc4); text-align: center; line-height: 48px; font-size: 24px">🎁</span><div style="flex: 1"><p style="margin: 0; font-weight: 800; color: #5f3dc4">Invite a friend</p><p style="margin: 2px 0 8px; font-size: 13px; color: #6741d9">You both get one month free.</p><a href="https://t.me/" target="_blank" style="${BTN}; padding: 6px 14px; background: #7048e8; color: #ffffff; font-size: 13px">Get my invite link</a></div></div>`,
  },
  {
    id: 'stats',
    group: 'sales',
    html: `<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; text-align: center"><div style="padding: 12px 6px; border-radius: 14px; background: #e6fcf5"><p style="margin: 0; font-size: 22px; font-weight: 900; color: #087f5b">99.9%</p><p style="margin: 2px 0 0; font-size: 12px; color: #0ca678">Uptime</p></div><div style="padding: 12px 6px; border-radius: 14px; background: #e7f5ff"><p style="margin: 0; font-size: 22px; font-weight: 900; color: #1864ab">20+</p><p style="margin: 2px 0 0; font-size: 12px; color: #1c7ed6">Locations</p></div><div style="padding: 12px 6px; border-radius: 14px; background: #fff0f6"><p style="margin: 0; font-size: 22px; font-weight: 900; color: #a61e4d">24/7</p><p style="margin: 2px 0 0; font-size: 12px; color: #d6336c">Support</p></div></div>`,
  },
  {
    id: 'testimonial',
    group: 'sales',
    html: `<div style="padding: 16px; border-radius: 16px; background: #ffffff; border: 1px solid #e9ecef; box-shadow: 0 8px 22px -14px rgba(0, 0, 0, 0.35)"><p style="margin: 0 0 6px; color: #fab005; font-size: 18px; letter-spacing: 2px">★★★★★</p><p style="margin: 0 0 12px; font-size: 15px; line-height: 1.6; font-style: italic; color: #343a40">“Stable every day, even on slow mobile data. The support team answered me in two minutes.”</p><div style="display: flex; align-items: center; gap: 10px"><span style="display: inline-block; width: 34px; height: 34px; border-radius: 999px; background: linear-gradient(135deg, #4dabf7, #455fe9); color: #ffffff; text-align: center; line-height: 34px; font-weight: 700">S</span><span style="font-weight: 700">Sara <span style="font-weight: 400; color: #868e96">· customer since 2024</span></span></div></div>`,
  },
  {
    id: 'apps',
    group: 'guide',
    html: `<p style="margin: 0 0 8px; font-weight: 700">📲 Download the app</p><div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px"><a href="https://play.google.com/" target="_blank" style="display: block; padding: 10px; border-radius: 12px; background: #212529; color: #ffffff; text-decoration: none; text-align: center; font-weight: 600">🤖 Android</a><a href="https://apps.apple.com/" target="_blank" style="display: block; padding: 10px; border-radius: 12px; background: #212529; color: #ffffff; text-decoration: none; text-align: center; font-weight: 600">🍎 iOS</a><a href="https://github.com/hiddify/hiddify-app/releases" target="_blank" style="display: block; padding: 10px; border-radius: 12px; background: #f1f3f5; color: #212529; text-decoration: none; text-align: center; font-weight: 600">🪟 Windows</a><a href="https://github.com/hiddify/hiddify-app/releases" target="_blank" style="display: block; padding: 10px; border-radius: 12px; background: #f1f3f5; color: #212529; text-decoration: none; text-align: center; font-weight: 600">💻 macOS</a></div>`,
  },
  {
    id: 'rules',
    group: 'guide',
    html: `<div style="padding: 14px; border-radius: 14px; background: #fff5f5; border: 1px solid #ffc9c9"><p style="margin: 0 0 10px; font-weight: 800; color: #c92a2a">📋 Please note</p><ol style="list-style: decimal; margin: 0; padding-inline-start: 20px; line-height: 1.9; color: #5c0f0f"><li>Use your account on at most 3 devices.</li><li>Do not share your subscription link.</li><li>Torrent downloads are not allowed.</li><li>Breaking a rule may suspend the account.</li></ol></div>`,
  },
  {
    id: 'tips',
    group: 'guide',
    html: `<div style="display: flex; gap: 12px; padding: 14px; border-radius: 14px; background: linear-gradient(135deg, #e3fafc, #e7f5ff); border: 1px solid #a5d8ff"><span style="font-size: 26px">💡</span><div><p style="margin: 0 0 4px; font-weight: 800; color: #1864ab">Tip: not connecting?</p><ul style="list-style: disc; margin: 0; padding-inline-start: 18px; line-height: 1.8; color: #1c4f7a"><li>Update your subscription in the app.</li><li>Try another config from the list.</li><li>Turn the app off and on again.</li></ul></div></div>`,
  },
]
