const validateEmail = require('./validateEmail');

describe('validateEmail', () => {
  test('accepts valid email', () => {
    expect(validateEmail('user@example.com')).toBe(true);
  });

  test('rejects plain string without @', () => {
    expect(validateEmail('invalid')).toBe(false);
  });

  test('rejects email with empty domain label', () => {
    expect(validateEmail('user@.com')).toBe(false);
  });
});
