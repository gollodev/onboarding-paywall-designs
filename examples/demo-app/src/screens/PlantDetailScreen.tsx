import { View, Text } from 'react-native';
import { useTranslation } from 'react-i18next';

export default function PlantDetailScreen() {
  const { t } = useTranslation();
  return (<View><Text>{t('plantdetail.title')}</Text></View>);
}
