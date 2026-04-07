function formatDateInput(value) {
  return value.toISOString().slice(0, 10);
}

export function buildRollingDateRange({ hours = 0, days = 0 }, now = new Date()) {
  const end = new Date(now);
  const start = new Date(now);

  const shiftHours = Math.max(0, Number(hours) || 0);
  const shiftDays = Math.max(0, Number(days) || 0);

  if (shiftHours > 0) {
    start.setTime(start.getTime() - shiftHours * 60 * 60 * 1000);
  } else if (shiftDays > 0) {
    start.setDate(start.getDate() - (shiftDays - 1));
  }

  return {
    fromDate: formatDateInput(start),
    toDate: formatDateInput(end),
  };
}
