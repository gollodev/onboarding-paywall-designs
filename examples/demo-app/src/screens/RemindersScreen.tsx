import { View, Text } from 'react-native';
import { useTranslation } from 'react-i18next';

export default function RemindersScreen() {
  const { t } = useTranslation();
  return (<View><Text>{t('reminders.title')}</Text></View>);
}
