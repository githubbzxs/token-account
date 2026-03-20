import { useEffect, useRef, useState } from 'react';
import { usePrefersReducedMotion } from '../hooks/usePrefersReducedMotion';

type RollingNumberProps = {
  value: string;
  className?: string;
  title?: string;
};

type DigitToken = {
  kind: 'digit';
  digit: number;
};

type StaticToken = {
  kind: 'static';
  char: string;
};

type Token = DigitToken | StaticToken;

type RenderDigitToken = {
  kind: 'digit';
  digit: number;
  position: number;
  key: string;
  delay: number;
};

type RenderStaticToken = {
  kind: 'static';
  char: string;
  key: string;
};

type RenderToken = RenderDigitToken | RenderStaticToken;

const DIGIT_REEL = Array.from({ length: 60 }, (_, index) => index % 10);
const REEL_OFFSET = 20;

function tokenizeValue(value: string): Token[] {
  return Array.from(value).map((char) => {
    if (/\d/.test(char)) {
      return {
        kind: 'digit',
        digit: Number(char),
      };
    }

    return {
      kind: 'static',
      char,
    };
  });
}

function canRollDigitByDigit(previousTokens: Token[], nextTokens: Token[]): boolean {
  if (previousTokens.length !== nextTokens.length) {
    return false;
  }

  return previousTokens.every((token, index) => {
    const nextToken = nextTokens[index];

    if (token.kind !== nextToken.kind) {
      return false;
    }

    if (token.kind === 'static' && nextToken.kind === 'static') {
      return token.char === nextToken.char;
    }

    return true;
  });
}

function extractDigitSignature(tokens: Token[]): string {
  return tokens
    .filter((token): token is DigitToken => token.kind === 'digit')
    .map((token) => token.digit)
    .join('');
}

function compareDigitSignature(previousTokens: Token[], nextTokens: Token[]): number {
  const previousDigits = extractDigitSignature(previousTokens).replace(/^0+/, '') || '0';
  const nextDigits = extractDigitSignature(nextTokens).replace(/^0+/, '') || '0';

  if (previousDigits.length !== nextDigits.length) {
    return nextDigits.length > previousDigits.length ? 1 : -1;
  }

  if (previousDigits === nextDigits) {
    return 1;
  }

  return nextDigits > previousDigits ? 1 : -1;
}

function buildInitialRenderTokens(tokens: Token[]): RenderToken[] {
  const digitCount = tokens.filter((token) => token.kind === 'digit').length;
  let digitIndex = 0;

  return tokens.map((token, index) => {
    if (token.kind === 'static') {
      return {
        kind: 'static',
        char: token.char,
        key: `static-${index}-${token.char}`,
      };
    }

    const delay = Math.max(digitCount - digitIndex - 1, 0) * 18;
    digitIndex += 1;

    return {
      kind: 'digit',
      digit: token.digit,
      position: REEL_OFFSET + token.digit,
      key: `digit-${index}`,
      delay,
    };
  });
}

function buildNextRenderTokens(previousRenderTokens: RenderToken[], nextTokens: Token[], direction: number): RenderToken[] {
  const previousDigits = previousRenderTokens.filter((token): token is RenderDigitToken => token.kind === 'digit');
  const digitCount = nextTokens.filter((token) => token.kind === 'digit').length;
  let digitIndex = 0;

  return nextTokens.map((token, index) => {
    if (token.kind === 'static') {
      return {
        kind: 'static',
        char: token.char,
        key: `static-${index}-${token.char}`,
      };
    }

    const previousDigit = previousDigits[digitIndex] ?? {
      digit: 0,
      position: REEL_OFFSET,
    };
    const delta = direction >= 0
      ? (token.digit - previousDigit.digit + 10) % 10
      : -((previousDigit.digit - token.digit + 10) % 10);
    const delay = Math.max(digitCount - digitIndex - 1, 0) * 18;
    digitIndex += 1;

    return {
      kind: 'digit',
      digit: token.digit,
      position: previousDigit.position + delta,
      key: `digit-${index}`,
      delay,
    };
  });
}

function joinClassNames(...classNames: Array<string | undefined>): string {
  return classNames.filter(Boolean).join(' ');
}

function renderStaticChar(char: string): string {
  return char === ' ' ? '\u00A0' : char;
}

export function RollingNumber({ value, className, title }: RollingNumberProps) {
  const prefersReducedMotion = usePrefersReducedMotion();
  const previousTokensRef = useRef<Token[]>(tokenizeValue(value));
  const [mode, setMode] = useState<'roll' | 'fade'>(prefersReducedMotion ? 'fade' : 'roll');
  const [renderTokens, setRenderTokens] = useState<RenderToken[]>(() => buildInitialRenderTokens(previousTokensRef.current));
  const [fallbackValue, setFallbackValue] = useState(value);

  useEffect(() => {
    const nextTokens = tokenizeValue(value);

    if (prefersReducedMotion) {
      setMode('fade');
      setFallbackValue(value);
      setRenderTokens(buildInitialRenderTokens(nextTokens));
      previousTokensRef.current = nextTokens;
      return;
    }

    if (!canRollDigitByDigit(previousTokensRef.current, nextTokens)) {
      setMode('fade');
      setFallbackValue(value);
      setRenderTokens(buildInitialRenderTokens(nextTokens));
      previousTokensRef.current = nextTokens;
      return;
    }

    const direction = compareDigitSignature(previousTokensRef.current, nextTokens);
    setMode('roll');
    setRenderTokens((currentTokens) => buildNextRenderTokens(currentTokens, nextTokens, direction));
    previousTokensRef.current = nextTokens;
  }, [prefersReducedMotion, value]);

  if (mode === 'fade') {
    return (
      <span className={joinClassNames('rolling-number', 'rolling-number-fallback', className)} aria-label={value} title={title}>
        <span key={fallbackValue} className="rolling-number-fallback-text">
          {fallbackValue}
        </span>
      </span>
    );
  }

  return (
    <span className={joinClassNames('rolling-number', className)} aria-label={value} role="text" title={title}>
      {renderTokens.map((token) => {
        if (token.kind === 'static') {
          return (
            <span key={token.key} className="rolling-number-static" aria-hidden="true">
              {renderStaticChar(token.char)}
            </span>
          );
        }

        return (
          <span key={token.key} className="rolling-number-column" aria-hidden="true">
            <span
              className="rolling-number-track"
              style={{
                transform: `translateY(-${token.position}em)`,
                transitionDelay: `${token.delay}ms`,
              }}
            >
              {DIGIT_REEL.map((digit, index) => (
                <span key={`${token.key}-${index}`} className="rolling-number-cell">
                  {digit}
                </span>
              ))}
            </span>
          </span>
        );
      })}
    </span>
  );
}
