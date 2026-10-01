/** Capture rules shared by registration and admission; not identity verification. */
export function documentProblem(type: string | null, raw: string | null): string | null {
  const number = raw?.trim() ?? ''
  if (type === 'DNI') {
    return /^[0-9]{8}$/.test(number)
      ? null
      : 'El DNI debe contener exactamente 8 dígitos, sin letras ni separadores.'
  }
  if (type === 'CE' || type === 'PAS') {
    return /^[A-Za-z0-9]{1,30}$/.test(number)
      ? null
      : 'El CE o pasaporte debe contener de 1 a 30 letras o dígitos, sin espacios.'
  }
  return /^[A-Za-z0-9][A-Za-z0-9./-]{0,29}$/.test(number)
    ? null
    : 'Use hasta 30 letras, dígitos o separadores . / -, empezando por letra o dígito.'
}
