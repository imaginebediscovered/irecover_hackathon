export type WeatherSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface WeatherDisruption {
  airportCode: string;
  disruptionDate: string; // ISO date string
  weatherType: string;
  severity: WeatherSeverity;
  impact: string;
}

export const weatherDisruptions: WeatherDisruption[] = [
  { airportCode: 'JFK', disruptionDate: '2026-02-01', weatherType: 'CLEAR', severity: 'LOW', impact: 'Clear skies, no impact' },
  { airportCode: 'LAX', disruptionDate: '2026-02-01', weatherType: 'CLEAR', severity: 'LOW', impact: 'Clear conditions' },
  { airportCode: 'ORD', disruptionDate: '2026-02-01', weatherType: 'PARTLY_CLOUDY', severity: 'LOW', impact: 'Partly cloudy, no delays' },
  { airportCode: 'HKG', disruptionDate: '2026-02-01', weatherType: 'CLEAR', severity: 'LOW', impact: 'Clear skies' },
  { airportCode: 'SIN', disruptionDate: '2026-02-01', weatherType: 'CLEAR', severity: 'LOW', impact: 'Clear conditions' },
  { airportCode: 'ORD', disruptionDate: '2026-02-03', weatherType: 'SNOW', severity: 'HIGH', impact: 'Heavy snowfall 15-20cm. De-icing delays, reduced runway capacity. Delays 4-6 hours.' },
  { airportCode: 'ORD', disruptionDate: '2026-02-04', weatherType: 'SNOW', severity: 'CRITICAL', impact: 'Blizzard conditions. Airport operating at 30% capacity. Delays 8-12 hours.' },
  { airportCode: 'ORD', disruptionDate: '2026-02-05', weatherType: 'ICE', severity: 'MEDIUM', impact: 'Freezing conditions. De-icing required, delays 2-4 hours.' },
  { airportCode: 'JFK', disruptionDate: '2026-02-04', weatherType: 'SNOW', severity: 'HIGH', impact: 'Heavy snowfall 15-20cm. De-icing delays, reduced runway capacity.' },
  { airportCode: 'JFK', disruptionDate: '2026-02-05', weatherType: 'SNOW', severity: 'HIGH', impact: 'Continued snow. Airport partially closed. Delays 6+ hours.' },
  { airportCode: 'LHR', disruptionDate: '2026-02-04', weatherType: 'FOG', severity: 'CRITICAL', impact: 'Dense fog <200m visibility. CAT III operations only. Massive delays.' },
  { airportCode: 'LHR', disruptionDate: '2026-02-05', weatherType: 'FOG', severity: 'HIGH', impact: 'Persistent fog. Reduced capacity, delays 4-6 hours.' },
  { airportCode: 'SIN', disruptionDate: '2026-02-08', weatherType: 'THUNDERSTORM', severity: 'MEDIUM', impact: 'Afternoon thunderstorms causing 1-2 hour delays' },
  { airportCode: 'HKG', disruptionDate: '2026-02-10', weatherType: 'TYPHOON', severity: 'CRITICAL', impact: 'Typhoon approaching. Airport closed for 12+ hours. All flights cancelled.' },
  { airportCode: 'FRA', disruptionDate: '2026-02-12', weatherType: 'ICE', severity: 'HIGH', impact: 'Freezing rain. De-icing delays 3-5 hours.' },
  { airportCode: 'ATL', disruptionDate: '2026-02-14', weatherType: 'THUNDERSTORM', severity: 'MEDIUM', impact: 'Severe thunderstorms. Delays 2-3 hours.' },
  { airportCode: 'LAX', disruptionDate: '2026-02-15', weatherType: 'CLEAR', severity: 'LOW', impact: 'Perfect weather conditions' },
  { airportCode: 'DFW', disruptionDate: '2026-02-18', weatherType: 'FOG', severity: 'MEDIUM', impact: 'Morning fog. Delays until 10am.' },
  { airportCode: 'ORD', disruptionDate: '2026-02-20', weatherType: 'SNOW', severity: 'HIGH', impact: 'Another winter storm. Delays 4-6 hours.' },
  { airportCode: 'JFK', disruptionDate: '2026-02-22', weatherType: 'ICE', severity: 'CRITICAL', impact: 'Ice storm. Airport closed 6+ hours.' },
  { airportCode: 'LHR', disruptionDate: '2026-02-25', weatherType: 'FOG', severity: 'HIGH', impact: 'Heavy fog. Delays 3-5 hours.' },
  { airportCode: 'JFK', disruptionDate: '2026-02-28', weatherType: 'CLEAR', severity: 'LOW', impact: 'Excellent flying conditions' },
  { airportCode: 'LAX', disruptionDate: '2026-02-28', weatherType: 'CLEAR', severity: 'LOW', impact: 'Clear skies' },
  { airportCode: 'ORD', disruptionDate: '2026-02-28', weatherType: 'PARTLY_CLOUDY', severity: 'LOW', impact: 'Mild conditions' },
  { airportCode: 'HKG', disruptionDate: '2026-02-28', weatherType: 'CLEAR', severity: 'LOW', impact: 'Clear conditions' },
  { airportCode: 'SIN', disruptionDate: '2026-02-28', weatherType: 'CLEAR', severity: 'LOW', impact: 'Clear skies' },
];
