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

function daysInPreviousMonth(year: number, month: number): number {
  return new Date(Date.UTC(year, month - 1, 0)).getUTCDate()
}

/** Calculates elapsed calendar time without timezone-dependent day shifts. */
export function calculateCalendarAge(
  birthDate: string,
  referenceDate: string | Date,
): CalendarAge | null {
  const birth = parseCalendarDate(birthDate)
  const reference = parseCalendarDate(referenceDate)
  if (!birth || !reference) return null

  let years = reference.year - birth.year
  let months = reference.month - birth.month
  let days = reference.day - birth.day

  if (days < 0) {
    months -= 1
    days += daysInPreviousMonth(reference.year, reference.month)
  }
  if (months < 0) {
    years -= 1
    months += 12
  }

  return years < 0 ? null : { years, months, days }
}

export function formatCalendarAge(
  birthDate: string,
  referenceDate: string | Date,
): string | null {
  const age = calculateCalendarAge(birthDate, referenceDate)
  if (!age) return null

  return `${age.years} años, ${age.months} meses y ${age.days} días`
}
