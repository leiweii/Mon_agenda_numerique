const { spawnSync } = require('node:child_process');

const result = spawnSync(
  process.execPath,
  [require.resolve('react-scripts/scripts/test'), '--runInBand', ...process.argv.slice(2)],
  {
    stdio: 'inherit',
    env: { ...process.env, CI: 'true' },
  }
);

if (result.error) {
  console.error(result.error);
  process.exitCode = 1;
} else {
  process.exitCode = result.status ?? 1;
}
