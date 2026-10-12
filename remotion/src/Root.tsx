import {Composition} from 'remotion';
import {Showreel} from './Showreel';

// Matches the Python pipeline: 1920x1080, 30 fps, 60 s.
export const Root = () => (
  <Composition id="Showreel" component={Showreel} width={1920} height={1080} fps={30} durationInFrames={1800} />
);
