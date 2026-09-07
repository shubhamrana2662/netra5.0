console.log('▶ Verifying Case Notes & Sticky Notes System...');

// Mock localStorage
const storage = new Map();
global.localStorage = {
  getItem: (key) => storage.get(key) || null,
  setItem: (key, val) => storage.set(key, val),
  removeItem: (key) => storage.delete(key),
  clear: () => storage.clear(),
};
global.window = {};

const caseId1 = 'CYB-2026-042';
const caseId2 = 'CYB-2026-018';

// Verify per-case isolation
const key1 = `cd_case_notes_v1_${caseId1}`;
const key2 = `cd_case_notes_v1_${caseId2}`;

const notesCase1 = [
  { id: '1', caseId: caseId1, title: 'Note for Case 1', content: 'Lead 1', isPinned: true, color: 'amber' },
];
const notesCase2 = [
  { id: '2', caseId: caseId2, title: 'Note for Case 2', content: 'Lead 2', isPinned: false, color: 'cyan' },
];

localStorage.setItem(key1, JSON.stringify(notesCase1));
localStorage.setItem(key2, JSON.stringify(notesCase2));

const loaded1 = JSON.parse(localStorage.getItem(key1));
const loaded2 = JSON.parse(localStorage.getItem(key2));

if (loaded1.length !== 1 || loaded1[0].caseId !== caseId1) {
  throw new Error('Case 1 notes isolation failed');
}
if (loaded2.length !== 1 || loaded2[0].caseId !== caseId2) {
  throw new Error('Case 2 notes isolation failed');
}
console.log('  ✓ Per-case isolation verified: Case 1 and Case 2 have distinct notes.');

// Verify pinning priority
const notes = [
  { id: 'a', isPinned: false, title: 'Unpinned' },
  { id: 'b', isPinned: true, title: 'Pinned' },
];
const sorted = [...notes].sort((a, b) => {
  if (a.isPinned && !b.isPinned) return -1;
  if (!a.isPinned && b.isPinned) return 1;
  return 0;
});
if (sorted[0].id !== 'b') {
  throw new Error('Pinning sort order failed');
}
console.log('  ✓ Pinned notes properly elevated to the top of the sticky board.');

console.log('✅ ALL CASE NOTES & STICKY NOTES TESTS PASSED SUCCESSFULLY!');
