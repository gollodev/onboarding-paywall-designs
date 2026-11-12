import { View, Text } from 'react-native';
import { useTranslation } from 'react-i18next';

export default function IdentifyScreen() {
  const { t } = useTranslation();
  return (<View><Text>{t('identify.title')}</Text></View>);
}
