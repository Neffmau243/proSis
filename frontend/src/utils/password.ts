export const PASSWORD_LENGTH = 8
export const passwordPattern = /^\d{8}$/
export const passwordFormatMessage = 'La contraseña debe contener exactamente 8 dígitos.'

export function normalizeNumericPassword(value: string): string {
  return value.replace(/\D/g, '').slice(0, PASSWORD_LENGTH)
}
