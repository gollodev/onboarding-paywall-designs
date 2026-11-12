import Purchases from 'react-native-purchases';
import { useEffect, useState } from 'react';

export const ENTITLEMENT_ID = 'pro';
export const FREE_PLANT_LIMIT = 3;
export const PREMIUM_FEATURES = ['unlimited_plants', 'diagnose', 'journal'];

export function useEntitlement() {
  const [isPro, setIsPro] = useState(false);
  useEffect(() => {
    Purchases.getCustomerInfo().then((info) => setIsPro(!!info.entitlements.active[ENTITLEMENT_ID]));
  }, []);
  return isPro;
}

export function canAddPlant(count: number, isPro: boolean) {
  return isPro || count < FREE_PLANT_LIMIT;
}
