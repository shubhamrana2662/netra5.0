import { useRef, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Icon } from '../../components/icons';
import { prefersReducedMotion } from '../../lib/motion';
import { SpatialFieldCanvas } from './SpatialFieldCanvas';
import { useStoryProgress } from './useStoryProgress';
import { StoryHUD } from './components/StoryHUD';
import { StoryNarrative, computeTextIntensity } from './components/StoryNarrative';
import { startEnterTransition } from '../../app/EnterOverlay';
import s from './landing.module.css';

export function Landing() {
  const navigate = useNavigate();
  const storyRef = useRef<HTMLDivElement>(null);

  // Single source of truth: storyProgress ∈ [0.0, 1.0]
  const storyProgress = useStoryProgress(storyRef);
  const textIntensity = computeTextIntensity(storyProgress);
  const bgBlur = Math.round(textIntensity * 6);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 40);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', handleScroll);
      window.scrollTo(0, 0);
      document.documentElement.scrollTop = 0;
      document.body.scrollTop = 0;
    };
  }, []);

  const jumpTo = (targetProgress: number) => {
    const element = storyRef.current;
    if (!element) return;
    const scrollDistance = element.offsetHeight - window.innerHeight;
    const targetY = targetProgress * scrollDistance;
    window.scrollTo({
      top: targetY,
      behavior: prefersReducedMotion() ? 'auto' : 'smooth',
    });
  };

  const enter = () => {
    window.scrollTo(0, 0);
    navigate('/login');
  };

  return (
    <div className={s.landing}>
      {/* Fixed Persistent 3D Spatial Intelligence Environment with Dynamic Focus Blur */}
      <SpatialFieldCanvas storyProgress={storyProgress} blurAmount={bgBlur} />

      {/* Top Header Navigation */}
      <header className={scrolled ? `${s.nav} ${s.navScrolled}` : s.nav}>
        <div className={s.brand} onClick={() => jumpTo(0)}>
          <Icon name="logo" size={20} />
          <span className={s.wordmark}>CYBERDRISHTI</span>
        </div>

        <div className={s.navRight}>
          <nav className={s.navLinks} aria-label="Journey Milestones">
            <button className={s.navLink} onClick={() => jumpTo(0.20)}>Correlation</button>
            <button className={s.navLink} onClick={() => jumpTo(0.40)}>The Graph</button>
            <button className={s.navLink} onClick={() => jumpTo(0.60)}>Evidence</button>
            <button className={s.navLink} onClick={() => jumpTo(0.80)}>Patterns</button>
          </nav>
          <button
            className={s.navLink}
            style={{ color: '#93c5fd', fontWeight: 500, border: '1px solid rgba(147, 197, 253, 0.25)', borderRadius: '6px', padding: '6px 14px' }}
            onClick={() => navigate('/login')}
          >
            Officer Sign In
          </button>
          <button className={s.enterBtn} style={{ padding: '8px 18px', fontSize: '12px' }} onClick={enter}>
            Enter Workspace →
          </button>
        </div>
      </header>

      {/* Story Chapter Navigation Side Rail */}
      <StoryHUD storyProgress={storyProgress} onJumpTo={jumpTo} />

      {/* Bottom Progress Scrubber Bar */}
      <div className={s.scrubber} aria-hidden="true">
        <div className={s.scrubberFill} style={{ width: `${(storyProgress * 100).toFixed(1)}%` }} />
      </div>

      {/* Physical 600vh Story Scroll Track */}
      <main ref={storyRef} className={s.scrollTrack}>
        <StoryNarrative storyProgress={storyProgress} onReplay={() => jumpTo(0)} />
      </main>
    </div>
  );
}
