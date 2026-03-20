import '@mantine/core/styles.css';
import '@mantine/charts/styles.css';
import '@mantine/dates/styles.css';
import './styles.css';

import React from 'react';
import ReactDOM from 'react-dom/client';
import { ColorSchemeScript, MantineProvider, createTheme } from '@mantine/core';

import { App } from './App';

const theme = createTheme({
  primaryColor: 'blue',
  fontFamily: '"Instrument Sans", "SF Pro Display", "SF Pro Text", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif',
  headings: {
    fontFamily: '"Instrument Sans", "SF Pro Display", "SF Pro Text", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif',
    fontWeight: '600',
  },
  defaultRadius: 'xl',
  colors: {
    blue: [
      '#ecf6ff',
      '#d7ebff',
      '#b4d9ff',
      '#8bc4ff',
      '#63afff',
      '#429dff',
      '#248cf8',
      '#0f73d6',
      '#0a5bac',
      '#094a88',
    ],
  },
  shadows: {
    md: '0 18px 50px rgba(112, 134, 167, 0.14)',
    xl: '0 40px 100px rgba(111, 131, 162, 0.2)',
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ColorSchemeScript defaultColorScheme="light" />
    <MantineProvider theme={theme} defaultColorScheme="light">
      <App />
    </MantineProvider>
  </React.StrictMode>,
);
