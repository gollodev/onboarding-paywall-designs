import { canAddPlant, FREE_PLANT_LIMIT } from '../src/premium/entitlements';

describe('premium limits', () => {
  it('limits free users to 3 plants', () => {
    expect(canAddPlant(FREE_PLANT_LIMIT, false)).toBe(false);
  });
  it('allows unlimited plants with pro entitlement', () => {
    expect(canAddPlant(50, true)).toBe(true);
  });
});
