export interface CalendarAge {
  years: number
  months: number
  days: number
}

interface CalendarDate {
  year: number
  month: number
  day: number
}

function parseCalendarDate(value: string | Date): CalendarDate | null {
  if (value instanceof Date) {
    if (Number.isNaN(value.getTime())) return null
    return {
      year: value.getFullYear(),
      month: value.getMonth() + 1,
      day: value.getDate(),
    }
  }

  const source = value.slice(0, 10)
  const [year, month, day] = source.split('-').map(Number)

  if (!year || !month || !day) return null

  const parsed = new Date(Date.UTC(year, month - 1, day))
  if (
    parsed.getUTCFullYear() !== year ||
    parsed.getUTCMonth() !== month - 1 ||
    parsed.getUTCDate() !== day
  ) {
    return null
  }

  return { year, month, day }
}

/** Último día del mes indicado (el mes se expresa en base 1). */
function lastDayOfMonth(year: number, month: number): number {
  return new Date(Date.UTC(year, month, 0)).getUTCDate()
}

/**
 * Suma meses a una fecha recortando el día al último disponible: quien nace el
 * 31 de enero cumple mes el 28 de febrero, igual que lo hace un calendario.
 */
function addMonths(date: CalendarDate, count: number): CalendarDate {
  const zeroBased = date.month - 1 + count
  const year = date.year + Math.floor(zeroBased / 12)
  const month = (((zeroBased % 12) + 12) % 12) + 1
  return { year, month, day: Math.min(date.day, lastDayOfMonth(year, month)) }
}

function compareDates(left: CalendarDate, right: CalendarDate): number {
  return (
    Date.UTC(left.year, left.month - 1, left.day) -
    Date.UTC(right.year, right.month - 1, right.day)
  )
}

function daysBetween(from: CalendarDate, to: CalendarDate): number {
  const start = Date.UTC(from.year, from.month - 1, from.day)
  const end = Date.UTC(to.year, to.month - 1, to.day)
  return Math.round((end - start) / 86_400_000)
}

/** Calculates elapsed calendar time without timezone-dependent day shifts. */
export function calculateCalendarAge(
  birthDate: string,
  referenceDate: string | Date,
): CalendarAge | null {
  const birth = parseCalendarDate(birthDate)
  const reference = parseCalendarDate(referenceDate)
  if (!birth || !reference) return null

  // Se avanza mes a mes desde el nacimiento y luego se cuentan los días
  // restantes: así nunca aparecen días negativos cuando el día de referencia
  // es anterior al del nacimiento.
  let months = (reference.year - birth.year) * 12 + (reference.month - birth.month)
  let anniversary = addMonths(birth, months)
  if (compareDates(anniversary, reference) > 0) {
    months -= 1
    anniversary = addMonths(birth, months)
  }
  if (months < 0) return null

  return {
    years: Math.floor(months / 12),
    months: months % 12,
    days: daysBetween(anniversary, reference),
  }
}

export function formatCalendarAge(
  birthDate: string,
  referenceDate: string | Date,
): string | null {
  const age = calculateCalendarAge(birthDate, referenceDate)
  if (!age) return null

  return `${age.years} años, ${age.months} meses y ${age.days} días`
}
