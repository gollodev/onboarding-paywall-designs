import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useColorScheme } from 'react-native';
import HomeScreen from '../screens/HomeScreen';
import IdentifyScreen from '../screens/IdentifyScreen';
import PlantDetailScreen from '../screens/PlantDetailScreen';
import RemindersScreen from '../screens/RemindersScreen';
import DiagnoseScreen from '../screens/DiagnoseScreen';
import JournalScreen from '../screens/JournalScreen';

const Stack = createNativeStackNavigator();

export default function RootNavigator() {
  const scheme = useColorScheme();
  return (
    <Stack.Navigator>
      <Stack.Screen name="Home" component={HomeScreen} />
      <Stack.Screen name="Identify" component={IdentifyScreen} />
      <Stack.Screen name="PlantDetail" component={PlantDetailScreen} />
      <Stack.Screen name="Reminders" component={RemindersScreen} />
      <Stack.Screen name="Diagnose" component={DiagnoseScreen} />
      <Stack.Screen name="Journal" component={JournalScreen} />
    </Stack.Navigator>
  );
}
