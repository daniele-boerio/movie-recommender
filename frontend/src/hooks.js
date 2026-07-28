import { useEffect, useRef, useState } from 'react';

/**
 * Vero quando l'utente sta scendendo nella pagina: serve a ritrarre una barra appiccicata
 * in alto mentre si scorre in giù e a rimostrarla appena si risale.
 *
 * - `threshold`: finché si è più in alto di così la barra resta sempre visibile — vicino
 *   alla cima è ancora al suo posto naturale e nasconderla sarebbe solo un tremolio.
 * - `delta`: quanto deve muoversi lo scroll prima di cambiare idea. Senza, il rimbalzo
 *   elastico di iOS e i micro-movimenti del dito la farebbero lampeggiare.
 */
export function useHideOnScroll({ threshold = 140, delta = 8 } = {}) {
  const [hidden, setHidden] = useState(false);
  const lastY = useRef(0);

  useEffect(() => {
    lastY.current = window.scrollY;
    let frame = null;

    const onScroll = () => {
      if (frame) return; // un solo calcolo per frame, non uno per evento
      frame = requestAnimationFrame(() => {
        frame = null;
        const y = window.scrollY;
        const diff = y - lastY.current;
        // Sotto la soglia non aggiorniamo `lastY`: così i movimenti piccoli si sommano
        // invece di essere buttati via, e uno scroll lento continua a funzionare.
        if (Math.abs(diff) < delta) return;
        lastY.current = y;
        setHidden(diff > 0 && y > threshold);
      });
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', onScroll);
      if (frame) cancelAnimationFrame(frame);
    };
  }, [threshold, delta]);

  return hidden;
}
