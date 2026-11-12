/** Adding my passkey on every domain of the panel: here first (the click lets the device's prompt open), then each
 * other domain's page in a frame (PasskeyDomainsDialog), one after the other (see hiddifypanel/passkeys.py). Each
 * passkey is named after the device. */
import { ref } from 'vue'
import { adminsApi, type PasskeyStep } from '@/features/admins/api'
import { createPasskey, PasskeyCancelled, PasskeyExists } from '@/shared/utils/webauthn'

/** Bumped after a passkey is added anywhere (e.g. from the suggestion), so the My account list reloads. */
export const passkeysVersion = ref(0)

/** Also read by the sign-in page (same site): this browser has a passkey here, so it asks for it right away. */
const REMEMBER_KEY = 'hiddify_passkey'

/**
 * Makes a passkey here (this device's; another device can add its own here too), then returns the other domains'
 * steps (empty: none left), and whether one was made here. When this device already has one here, it goes on to the other domains.
 * Must run from a click: browsers only show the passkey prompt after one.
 */
export async function addPasskeyHere(here: string | null, missing: string[]): Promise<{ added: boolean; steps: PasskeyStep[] }> {
  const others = missing.some((d) => d !== here)
  let added = false
  if (here) {
    try {
      const options = await adminsApi.passkeyOptions()
      const credential = await createPasskey(options)
      await adminsApi.addPasskey('', credential)
      added = true
      passkeysVersion.value++
    } catch (e) {
      if (!(e instanceof PasskeyExists) || !others) throw e
    }
    try {
      localStorage.setItem(REMEMBER_KEY, '1')
    } catch {
      // private window: the sign-in page still offers it in the username suggestions and by its button
    }
  }
  return { added, steps: others ? await adminsApi.passkeyTour() : [] }
}

const KNOWN_ERRORS = ['exists', 'unsupported', 'not_verified', 'expired']

/** The translation key for why adding failed (`null`: show the server's own message). */
export function passkeyErrorKey(error: unknown): string | null {
  if (error instanceof PasskeyCancelled) return 'account.passkeys.cancelled'
  if (error instanceof PasskeyExists) return 'account.passkeys.error.exists'
  const code = (error as { response?: { data?: { code?: string } } })?.response?.data?.code
  if (code === 'needs_domain') return 'account.passkeys.needsDomain'
  return code && KNOWN_ERRORS.includes(code) ? `account.passkeys.error.${code}` : null
}
