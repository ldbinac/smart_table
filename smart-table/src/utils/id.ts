export function generateId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 11)}`;
}

export function generateShortId(): string {
  return Math.random().toString(36).substring(2, 11);
}

export function generateNumericId(length: number = 8): string {
  let result = '';
  for (let i = 0; i < length; i++) {
    result += Math.floor(Math.random() * 10).toString();
  }
  return result;
}
