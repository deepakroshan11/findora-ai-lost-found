import React, { useState, act } from 'react';
import { createRoot } from 'react-dom/client';
import AgentChat, { useAgentChat } from './AgentChat';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

let container;
let root;

beforeEach(() => {
  sessionStorage.clear();
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  Element.prototype.scrollTo = () => {};
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  delete global.fetch;
});

const fakeChat = (messages, extra = {}) => ({ messages, busy: false, send: jest.fn(), reset: jest.fn(), ...extra });

const ITEM = {
  item_id: 'f1', title: 'Black leather wallet', description: 'Tan stitching', item_type: 'found',
  location: 'Central Library', created_at: '2026-11-22T10:00:00', status: 'active',
  image_path: 'https://res.cloudinary.com/demo/wallet.jpg', reported_by: 'Priya K.', reward_amount: 0,
};

test('formats bold text and lists instead of showing asterisks', () => {
  const chat = fakeChat([
    { role: 'user', content: 'list items' },
    { role: 'assistant', content: 'Would you like to:\n\n1. **See found keys**\n2. **Draft a report**' },
  ]);
  act(() => root.render(<AgentChat chat={chat} demo={false} onSignIn={() => {}} onPrefillReport={() => {}} />));
  expect(container.textContent).not.toContain('**');
  expect(container.querySelectorAll('ol li')).toHaveLength(2);
  expect(container.querySelector('ol strong').textContent).toBe('See found keys');
});

test('shows item cards with photo, type, place and reporter', () => {
  const chat = fakeChat([{ role: 'assistant', content: 'I found 1 report.', items: [ITEM], steps: [{ tool: 'search_items', ok: true }] }]);
  act(() => root.render(<AgentChat chat={chat} demo={false} onSignIn={() => {}} onPrefillReport={() => {}} />));
  expect(container.querySelector('img').getAttribute('src')).toBe(ITEM.image_path);
  expect(container.textContent).toContain('FOUND');
  expect(container.textContent).toContain('Central Library');
  expect(container.textContent).toContain('Reported by Priya K.');
});

test('demo mode shows the sign-in banner', () => {
  const onSignIn = jest.fn();
  const chat = fakeChat([{ role: 'assistant', content: 'Hi', local: true }]);
  act(() => root.render(<AgentChat chat={chat} demo onSignIn={onSignIn} onPrefillReport={() => {}} />));
  expect(container.textContent).toContain("You're in demo mode");
  const btn = [...container.querySelectorAll('button')].find((b) => b.textContent === 'Sign in');
  act(() => btn.click());
  expect(onSignIn).toHaveBeenCalled();
});

test('conversation survives switching tabs, even while an answer is on its way', async () => {
  let resolveFetch;
  global.fetch = jest.fn(() => new Promise((r) => { resolveFetch = r; }));
  let api;
  let setTab;

  function App() {
    const [tab, _setTab] = useState('assistant');
    setTab = _setTab;
    const chat = useAgentChat('http://api', 'user-1');
    api = chat;
    return tab === 'assistant'
      ? <AgentChat chat={chat} demo={false} onSignIn={() => {}} onPrefillReport={() => {}} />
      : <p>Browse tab</p>;
  }

  act(() => root.render(<App />));
  await act(async () => { api.send('I lost my wallet'); });
  act(() => setTab('browse'));                          // user leaves mid-answer
  expect(container.textContent).toBe('Browse tab');

  await act(async () => {
    resolveFetch({ ok: true, json: async () => ({ reply: 'Found **1** wallet.', steps: [], actions: [], items: [ITEM] }) });
  });
  act(() => setTab('assistant'));                       // and comes back

  expect(container.textContent).toContain('I lost my wallet');
  expect(container.textContent).toContain('Found 1 wallet.');
  expect(container.textContent).toContain('Black leather wallet');
  const body = JSON.parse(global.fetch.mock.calls[0][1].body);
  expect(body.user_id).toBe('user-1');
  expect(body.messages).toEqual([{ role: 'user', content: 'I lost my wallet' }]);   // greeting not sent
  expect(JSON.parse(sessionStorage.getItem('findora-chat:user-1'))).toHaveLength(3);
});
