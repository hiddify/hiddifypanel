/**
 * Ready-made designs for the support box (Full mode's template gallery). Only tags and CSS the panel keeps when it saves
 * the text (hutils/user_html): inline styles, no positioning, no url(). Each one is short, so it fits the setting's limit.
 */

export interface SupportTemplate {
  id: string
  html: string
}

const BTN = 'display: inline-block; padding: 8px 16px; border-radius: 999px; font-weight: 600; text-decoration: none'

export const TEMPLATES: SupportTemplate[] = [
  {
    id: 'hero',
    html: `<div style="padding: 16px; border-radius: 16px; background: linear-gradient(135deg, #4f46e5, #06b6d4); color: #ffffff; text-align: center"><p style="margin: 0 0 4px; font-size: 18px; font-weight: 700">💬 24/7 Support</p><p style="margin: 0 0 12px; opacity: 0.9">Questions? We answer within minutes.</p><a href="https://t.me/" target="_blank" style="${BTN}; background: #ffffff; color: #4f46e5">Telegram</a></div>`,
  },
  {
    id: 'contacts',
    html: `<div style="display: flex; flex-direction: column; gap: 8px"><a href="https://t.me/" target="_blank" style="display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 12px; background: #ffffff; color: #212529; text-decoration: none; border: 1px solid #dee2e6">✈️ <b>Telegram</b><span style="margin-inline-start: auto; color: #455fe9">@support</span></a><a href="mailto:support@example.com" style="display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 12px; background: #ffffff; color: #212529; text-decoration: none; border: 1px solid #dee2e6">✉️ <b>Email</b><span style="margin-inline-start: auto; color: #455fe9">support@example.com</span></a><a href="tel:+10000000000" style="display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 12px; background: #ffffff; color: #212529; text-decoration: none; border: 1px solid #dee2e6">📞 <b>Phone</b><span style="margin-inline-start: auto; color: #455fe9">+1 000 000 0000</span></a></div>`,
  },
  {
    id: 'announcement',
    html: `<div style="padding: 12px 14px; border-radius: 12px; background: #fff9db; border: 1px solid #ffe066; color: #5c4400"><p style="margin: 0 0 4px; font-weight: 700">📢 Announcement</p><p style="margin: 0">New servers are online. Update your subscription in the app to use them.</p></div>`,
  },
  {
    id: 'alerts',
    html: `<div style="display: flex; flex-direction: column; gap: 8px"><div style="padding: 10px 12px; border-radius: 10px; background: #ebfbee; border-inline-start: 4px solid #2f9e44; color: #1b5e2b">✅ All servers are working normally.</div><div style="padding: 10px 12px; border-radius: 10px; background: #e7f5ff; border-inline-start: 4px solid #1971c2; color: #0b4a7d">ℹ️ Scheduled maintenance on Friday, 02:00–03:00.</div><div style="padding: 10px 12px; border-radius: 10px; background: #fff4e6; border-inline-start: 4px solid #f76707; color: #7a3300">⚠️ Renew before your plan ends to keep your settings.</div></div>`,
  },
  {
    id: 'faq',
    html: `<div style="display: flex; flex-direction: column; gap: 6px"><details style="padding: 10px 12px; border-radius: 10px; background: #ffffff; border: 1px solid #dee2e6"><summary style="font-weight: 600">How do I connect?</summary><p style="margin: 8px 0 0">Install the app, then import your subscription link.</p></details><details style="padding: 10px 12px; border-radius: 10px; background: #ffffff; border: 1px solid #dee2e6"><summary style="font-weight: 600">It does not connect, what now?</summary><p style="margin: 8px 0 0">Update the subscription, switch to another config, or message support.</p></details></div>`,
  },
  {
    id: 'columns',
    html: `<div style="display: flex; gap: 8px"><div style="flex: 1; padding: 12px; border-radius: 12px; background: #ffffff; border: 1px solid #dee2e6; text-align: center"><p style="margin: 0 0 4px; font-size: 22px">✈️</p><p style="margin: 0 0 8px; font-weight: 600">Telegram</p><a href="https://t.me/" target="_blank" style="color: #455fe9; text-decoration: underline">Open</a></div><div style="flex: 1; padding: 12px; border-radius: 12px; background: #ffffff; border: 1px solid #dee2e6; text-align: center"><p style="margin: 0 0 4px; font-size: 22px">✉️</p><p style="margin: 0 0 8px; font-weight: 600">Email</p><a href="mailto:support@example.com" style="color: #455fe9; text-decoration: underline">Write</a></div></div>`,
  },
  {
    id: 'plan',
    html: `<div style="padding: 16px; border-radius: 16px; background: #ffffff; border: 2px solid #455fe9; box-shadow: 0 8px 24px -12px rgba(69, 95, 233, 0.5)"><p style="margin: 0; color: #455fe9; font-weight: 700">⭐ Premium</p><p style="margin: 4px 0 8px; font-size: 26px; font-weight: 800; color: #212529">$5 <span style="font-size: 14px; font-weight: 400; color: #868e96">/ month</span></p><ul style="list-style: none; margin: 0 0 12px; padding: 0; line-height: 1.9"><li>✔️ Unlimited traffic</li><li>✔️ 3 devices</li><li>✔️ Priority support</li></ul><a href="https://t.me/" target="_blank" style="${BTN}; background: #455fe9; color: #ffffff">Renew now</a></div>`,
  },
  {
    id: 'hours',
    html: `<p style="margin: 0 0 6px; font-weight: 700">🕒 Support hours</p><table style="width: 100%; border-collapse: collapse; background: #ffffff; border-radius: 10px"><tbody><tr><td style="padding: 6px 10px; border-bottom: 1px solid #e9ecef">Sat – Wed</td><td style="padding: 6px 10px; border-bottom: 1px solid #e9ecef; text-align: end">09:00 – 23:00</td></tr><tr><td style="padding: 6px 10px; border-bottom: 1px solid #e9ecef">Thursday</td><td style="padding: 6px 10px; border-bottom: 1px solid #e9ecef; text-align: end">09:00 – 18:00</td></tr><tr><td style="padding: 6px 10px">Friday</td><td style="padding: 6px 10px; text-align: end; color: #e03131">Closed</td></tr></tbody></table>`,
  },
  {
    id: 'social',
    html: `<p style="margin: 0 0 8px; text-align: center; font-weight: 600">Follow us</p><div style="display: flex; flex-wrap: wrap; gap: 6px; justify-content: center"><a href="https://t.me/" target="_blank" style="${BTN}; background: #229ed9; color: #ffffff">Telegram</a><a href="https://instagram.com/" target="_blank" style="${BTN}; background: #d6336c; color: #ffffff">Instagram</a><a href="https://x.com/" target="_blank" style="${BTN}; background: #212529; color: #ffffff">X</a><a href="https://youtube.com/" target="_blank" style="${BTN}; background: #e03131; color: #ffffff">YouTube</a></div>`,
  },
  {
    id: 'steps',
    html: `<p style="margin: 0 0 8px; font-weight: 700">🚀 Get started in 3 steps</p><ol style="list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px"><li style="display: flex; gap: 10px; align-items: center"><span style="display: inline-block; width: 24px; height: 24px; border-radius: 999px; background: #455fe9; color: #ffffff; text-align: center; line-height: 24px; font-weight: 700">1</span>Install the Hiddify app</li><li style="display: flex; gap: 10px; align-items: center"><span style="display: inline-block; width: 24px; height: 24px; border-radius: 999px; background: #455fe9; color: #ffffff; text-align: center; line-height: 24px; font-weight: 700">2</span>Import your subscription link</li><li style="display: flex; gap: 10px; align-items: center"><span style="display: inline-block; width: 24px; height: 24px; border-radius: 999px; background: #455fe9; color: #ffffff; text-align: center; line-height: 24px; font-weight: 700">3</span>Tap Connect</li></ol>`,
  },
]
