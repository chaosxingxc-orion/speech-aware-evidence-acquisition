/** Own-app subscription sign-in; never read another application's credentials. */
import { spawn, spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, statSync } from 'node:fs';
import { basename, isAbsolute, join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const sdkCommit = 'f723814abdccec135b519c451fb6e1992ee5e933';
if (process.platform !== 'win32') throw new Error('This credential adapter requires Windows DPAPI.');
// Interactive packaged applications can virtualize this logical directory.
// A background registration supplies its handle-resolved physical own-app path.
const windowsPowerShell = 'C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe';
const knownFolder = spawnSync(windowsPowerShell, ['-NoProfile', '-NonInteractive', '-Command',
  '[Console]::Out.Write([Environment]::GetFolderPath([Environment+SpecialFolder]::LocalApplicationData))'],
  {encoding: 'utf8', windowsHide: true, timeout: 10000});
if (knownFolder.status !== 0 || !knownFolder.stdout.trim()) throw new Error('Own-app storage directory is unavailable.');
const root = process.argv[3] ?? join(knownFolder.stdout.trim(), 'saea-system-proposer');
if (!isAbsolute(root) || resolve(root) !== root || basename(root) !== 'saea-system-proposer') {
  throw new Error('The registered own-app directory is invalid.');
}
const sdk = join(root, 'devkit-f723814');
const command = process.argv[2] ?? 'status';
if (!['status', 'signin', 'self-test', 'source-check', 'models', 'credential-pipe'].includes(command)) throw new Error('Unsupported command.');
if (command === 'credential-pipe' && (process.stdout.isTTY || process.env.SAEA_AUTH_INTERNAL_PIPE !== '1')) {
  throw new Error('Credentials are available only to the registered private subprocess pipe.');
}

function dpapi(mode, input) {
  const operation = mode === 'protect' ? 'Protect' : 'Unprotect';
  const script = `Add-Type -AssemblyName System.Security
    $bytes = [Convert]::FromBase64String([Console]::In.ReadToEnd())
    $value = [Security.Cryptography.ProtectedData]::${operation}($bytes, $null,
      [Security.Cryptography.DataProtectionScope]::CurrentUser)
    [Console]::Out.Write([Convert]::ToBase64String($value))`;
  const result = spawnSync(windowsPowerShell, ['-NoProfile', '-NonInteractive', '-Command', script], {
    input: Buffer.from(input).toString('base64'), encoding: 'utf8', windowsHide: true,
    timeout: 10000, maxBuffer: 4 * 1024 * 1024,
  });
  if (result.status !== 0 || result.error) throw new Error('DPAPI operation failed; no plaintext persistence is permitted.');
  return Buffer.from(result.stdout.trim(), 'base64');
}

const encryption = {
  id: 'saea-windows-dpapi-current-user-v1',
  isAvailable: () => process.platform === 'win32',
  encrypt: (value) => dpapi('protect', Buffer.from(value, 'utf8')),
  decrypt: (value) => dpapi('unprotect', value).toString('utf8'),
};
if (command === 'self-test') {
  const text = 'Synthetic credential adapter round trip; not a real credential.';
  if (encryption.decrypt(encryption.encrypt(text)) !== text) throw new Error('Credential adapter round trip failed.');
  console.log(JSON.stringify({credential_adapter: encryption.id, round_trip: true, model_calls: 0}));
  process.exit(0);
}
// Pin the installed executable instead of relying on background PATH lookup.
const git = 'C:\\Program Files\\Git\\cmd\\git.exe';
const head = spawnSync(git, ['-C', sdk, 'rev-parse', 'HEAD'], {encoding: 'utf8', windowsHide: true});
const clean = spawnSync(git, ['-C', sdk, 'diff', '--exit-code', '--', 'packages/local/src'], {windowsHide: true});
if (command === 'source-check') {
  const lookup = spawnSync('git', ['--version'], {encoding: 'utf8', windowsHide: true});
  let sourceError = null;
  try { statSync(sdk); } catch (error) { sourceError = error.code; }
  console.log(JSON.stringify({sdk_source_verified: head.status === 0 && head.stdout.trim() === sdkCommit && clean.status === 0,
    sdk_path: sdk, source_error: sourceError,
    sdk_exists: existsSync(sdk), explicit_app_root: Boolean(process.argv[3]), head_status: head.status, clean_status: clean.status,
    head_error: head.error?.code ?? null, clean_error: clean.error?.code ?? null,
    head_commit_matches: head.stdout?.trim() === sdkCommit,
    git_stderr_markers: ['dubious ownership', 'not a git repository', 'Permission denied'].filter(s => (head.stderr ?? '').includes(s)), explicit_git: true,
    path_git_available: lookup.status === 0, path_git_error: lookup.error?.code ?? null,
    credential_reads: 0, model_calls: 0}));
  process.exit(0);
}
if (head.status !== 0 || head.stdout.trim() !== sdkCommit || clean.status !== 0) throw new Error('Official SDK source pin differs.');
mkdirSync(root, {recursive: true});
const { createChatGPT } = await import(pathToFileURL(join(sdk, 'packages/local/dist/index.js')));
const client = createChatGPT({
  appName: 'SAEA System Text Research', appId: 'saea-system-text-research',
  redirectPort: 0, storageDir: join(root, 'oauth'), credentialEncryption: encryption,
  sendHostId: true,
  openBrowser(url) {
    const address = new URL(url);
    if (address.protocol !== 'https:' || address.hostname !== 'auth.openai.com') throw new Error('Unexpected authorization origin.');
    const browser = spawn('rundll32.exe', ['url.dll,FileProtocolHandler', url], {windowsHide: true, stdio: 'ignore'});
    browser.on('error', () => client.cancelSignIn());
  },
});
try {
  if (command === 'credential-pipe') {
    // The official client performs any required refresh and identity validation.
    // This program owns this store; it never opens a Codex or another app store.
    await client.listModels();
    const { ConnectionStore } = await import(pathToFileURL(join(sdk, 'packages/local/dist/storage.js')));
    const store = new ConnectionStore(join(root, 'oauth'), encryption);
    const credential = await store.withLock(async () => {
      const state = await store.read();
      const profile = state?.profiles.find((p) => p.id === state.activeProfileId);
      if (!profile || profile.status !== 'connected' || profile.pendingRefresh ||
          !profile.scopes.includes('chatgpt.tokens.use.direct') ||
          !profile.credentials || profile.credentials.expiresAt <= Date.now() + 10000) {
        throw new Error('Own-app credential is not ready.');
      }
      return profile.credentials.accessToken;
    });
    process.stdout.write(credential);
    process.exit(0);
  }
  if (command === 'models') {
    const models = await client.listModels();
    console.log(JSON.stringify({models, model_calls: 0, provider_admitted: false}));
    process.exit(0);
  }
  const session = command === 'signin' ? await client.signIn({label: 'SAEA research subscription'}) : await client.getSession();
  // Deliberately omit identity, profile ID, tokens and authorization URLs.
  console.log(JSON.stringify({status: session.status, sharing: session.sharing, model_calls: 0,
    provider_admitted: false, proposal_contacts: 0}));
} catch (error) {
  console.log(JSON.stringify({status: 'sign-in-incomplete', code: error.code ?? 'authentication_error',
    model_calls: 0, provider_admitted: false, proposal_contacts: 0}));
  process.exitCode = 1;
}
