import { View, Text } from 'react-native';
import { useEntitlement } from '../premium/entitlements';

// Premium: growth journal with photos.
export default function JournalScreen({ navigation }) {
  const isPro = useEntitlement();
  if (!isPro) navigation.navigate('Paywall', { source: 'journal_locked' });
  return (<View><Text>Journal</Text></View>);
}
