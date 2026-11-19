// Firefox paints SVG text while it is selected, even when fill is transparent.
// Those glyphs are a stand-in font, so they sit off the scan. HTML text with a
// transparent selection color leaves only the highlight, and copying still
// returns the word.
//
// The stand-in font is wider than the ink, especially in capitals. A guessed
// letter-spacing made that worse, so a drag along one line also hit the lines
// below. Each word is therefore clipped to its ink box, then scaled to that
// width once the browser has measured the real glyphs.

export function liftTransparentWords(svg) {
  const words = svg.querySelectorAll('text[fill="transparent"]');
  if (!words.length || !svg.parentNode) {
    return;
  }

  const box = svg.viewBox && svg.viewBox.baseVal;
  const boxWidth = (box && box.width) || number(svg.getAttribute('width'), 1) || 1;
  const boxHeight = (box && box.height) || number(svg.getAttribute('height'), 1) || 1;
  const pixelWidth = number(svg.style.width, number(svg.getAttribute('width'), boxWidth));
  const pixelHeight = number(svg.style.height, number(svg.getAttribute('height'), boxHeight));
  const scaleX = pixelWidth / boxWidth;
  const scaleY = pixelHeight / boxHeight;

  const layer = svg.ownerDocument.createElement('div');
  layer.className = 'scan-text-layer';
  layer.style.position = 'relative';
  layer.style.width = `${pixelWidth}px`;
  layer.style.height = `${pixelHeight}px`;
  svg.parentNode.insertBefore(layer, svg);
  layer.appendChild(svg);
  svg.style.position = 'absolute';
  svg.style.left = '0';
  svg.style.top = '0';

  words.forEach((word) => {
    const text = word.textContent || '';
    const fontSize = number(word.getAttribute('font-size'), 12) * scaleY;
    const x = number(word.getAttribute('x'), 0) * scaleX;
    const baseline = number(word.getAttribute('y'), 0) * scaleY;
    const textLength = number(word.getAttribute('textLength'), 0) * scaleX;
    const span = svg.ownerDocument.createElement('span');
    const inkHeight = fontSize / 0.8;
    span.className = 'scan-word';
    span.style.position = 'absolute';
    span.style.left = `${x}px`;
    span.style.top = `${baseline - inkHeight}px`;
    span.style.height = `${inkHeight}px`;
    span.style.lineHeight = '1';
    span.style.overflow = 'hidden';
    span.style.whiteSpace = 'pre';
    span.style.color = 'transparent';
    span.style.webkitTextFillColor = 'transparent';

    const letters = text.trim();
    if (!letters) {
      // The gap after a word. It stays in the copied text, but it must not
      // steal the hit target from the next word.
      span.textContent = ' ';
      span.style.width = '0';
      span.style.pointerEvents = 'none';
      layer.appendChild(span);
      word.remove();
      return;
    }

    span.style.width = `${textLength}px`;
    span.dataset.inkWidth = String(textLength);
    const inner = svg.ownerDocument.createElement('span');
    inner.className = 'scan-word-text';
    inner.textContent = letters;
    inner.style.display = 'inline-block';
    inner.style.fontSize = `${fontSize}px`;
    inner.style.fontFamily = word.getAttribute('font-family') || 'serif';
    inner.style.lineHeight = '1';
    inner.style.whiteSpace = 'pre';
    inner.style.color = 'transparent';
    inner.style.webkitTextFillColor = 'transparent';
    inner.style.transformOrigin = 'left center';
    span.appendChild(inner);
    layer.appendChild(span);
    word.remove();
  });
}

// Squeeze each word onto its ink box. Called after layout, because only then
// is the real glyph width known.
export function fitScanWords(root) {
  if (!root || !root.querySelectorAll) {
    return;
  }
  root.querySelectorAll('.scan-word-text').forEach((inner) => {
    const target = number(inner.parentNode && inner.parentNode.dataset.inkWidth, 0);
    if (!(target > 0)) {
      return;
    }
    inner.style.transform = 'none';
    const natural = inner.scrollWidth;
    if (!(natural > 0)) {
      return;
    }
    inner.style.transformOrigin = 'left center';
    inner.style.transform = `scaleX(${target / natural})`;
  });
}

function number(value, fallback) {
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}
