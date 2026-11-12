import { View, Text } from 'react-native';
import { useEntitlement } from '../premium/entitlements';

// Premium: photo diagnosis of pests and diseases.
export default function DiagnoseScreen({ navigation }) {
  const isPro = useEntitlement();
  if (!isPro) {
    navigation.navigate('Paywall', { source: 'diagnose_locked' });
    return null;
  }
  return (<View><Text>Diagnose</Text></View>);
}
