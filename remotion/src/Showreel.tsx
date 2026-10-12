import {AbsoluteFill, Img, Sequence, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {Audio} from '@remotion/media';

// Starter composition: one poster per beat (15 frames = 1 beat at 120 BPM).
// Replace with real shots; poster filenames live in ../assets/posters.
const posters: string[] = [];

export const Showreel = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 15], [0, 1], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{background: '#0a0a0a', color: '#fff', fontFamily: 'Inter, sans-serif'}}>
      <Audio src={staticFile('audio.wav')} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', opacity}}>
        <h1 style={{fontSize: 96, fontWeight: 800, margin: 0}}>Jeevan Saiesh Paramkusam</h1>
      </AbsoluteFill>
      {posters.map((p, i) => (
        <Sequence key={p} from={120 + i * 15} durationInFrames={15}>
          <Img src={staticFile(`posters/${p}`)} style={{height: '100%', objectFit: 'contain', margin: '0 auto'}} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
