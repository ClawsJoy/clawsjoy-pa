import type { NextPage } from 'next';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { useEffect, useState, useRef } from 'react';

// --- Types ---
interface KeyPair {
  publicKey: string;   // base64 (raw)
  privateKey: string;  // base64 (pkcs8 raw)
}

type PageState = 'init' | 'generating' | 'backup_prompt' | 'login' | 'import_key' | 'loading' | 'error' | 'success';

// --- Ed25519 helpers using Web Crypto API ---
async function generateEd25519KeyPair(): Promise<KeyPair> {
  const keyPair = await crypto.subtle.generateKey(
    { name: 'Ed25519' },
    true,
    ['sign', 'verify']
  );

  const [pubRaw, privRaw] = await Promise.all([
    crypto.subtle.exportKey('raw', keyPair.publicKey),
    crypto.subtle.exportKey('pkcs8', keyPair.privateKey),
  ]);

  const publicKey = btoa(String.fromCharCode(...new Uint8Array(pubRaw)));
  const privateKey = btoa(String.fromCharCode(...new Uint8Array(privRaw)));

  return { publicKey, privateKey };
}

function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

async function signChallenge(privateKeyBase64: string, challenge: string): Promise<string> {
  const pkcs8Raw = base64ToArrayBuffer(privateKeyBase64);
  const privateKey = await crypto.subtle.importKey(
    'pkcs8',
    pkcs8Raw,
    { name: 'Ed25519' },
    false,
    ['sign']
  );
  const encoder = new TextEncoder();
  const signature = await crypto.subtle.sign(
    'Ed25519',
    privateKey,
    encoder.encode(challenge)
  );
  return btoa(String.fromCharCode(...new Uint8Array(signature)));
}

// --- Progress animation messages ---
const PROGRESS_MESSAGES = [
  '正在初始化安全环境...',
  '正在生成高强度密钥对...',
  '正在优化密钥参数...',
  '密钥生成完成！',
];

// --- Component ---
const RegisterPage: NextPage = () => {
  const router = useRouter();

  const [pageState, setPageState] = useState<PageState>('init');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [progressText, setProgressText] = useState<string>('正在生成密钥...');
  const [generatedKeyPair, setGeneratedKeyPair] = useState<KeyPair | null>(null);
  const [storedPrivateKey, setStoredPrivateKey] = useState<string | null>(null);
  const [storedPublicKey, setStoredPublicKey] = useState<string | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // On mount, check if user already has a private key in localStorage
  useEffect(() => {
    const savedKey = localStorage.getItem('clawsjoy_private_key');
    const savedPub = localStorage.getItem('clawsjoy_public_key');
    if (savedKey) {
      setStoredPrivateKey(savedKey);
      setStoredPublicKey(savedPub);
      setPageState('login');
    }
  }, []);

  // Run progress animation during key generation
  const runProgressAnimation = () => {
    setProgress(0);
    const totalSteps = PROGRESS_MESSAGES.length;
    let step = 0;
    const interval = setInterval(() => {
      step++;
      if (step < totalSteps) {
        setProgressText(PROGRESS_MESSAGES[step]);
        setProgress(Math.round((step / totalSteps) * 100));
      } else {
        clearInterval(interval);
      }
    }, 800);
    return interval;
  };

  // ===== Scenario 1: First-time Registration =====
  const handleStartRegister = async () => {
    setPageState('generating');
    setErrorMsg(null);
    setProgressText(PROGRESS_MESSAGES[0]);
    setProgress(5);

    const animInterval = runProgressAnimation();

    try {
      // Step 1: Generate Ed25519 key pair
      const keyPair = await generateEd25519KeyPair();
      clearInterval(animInterval);
      setProgressText('密钥生成完成！');
      setProgress(100);
      setGeneratedKeyPair(keyPair);

      // Step 2: Store public key temporarily, redirect to agreement page
      const stateParam = encodeURIComponent(
        JSON.stringify({ pub: keyPair.publicKey })
      );
      router.push(`/agree?type=platform&redirect=register&state=${stateParam}`);
      return;
    } catch (err: any) {
      clearInterval(animInterval);
      setErrorMsg(err.message || '密钥生成失败');
      setPageState('error');
    }
  };

  // Called after agreement is signed — completes registration
  const handleCompleteRegistration = async (keyPair: KeyPair) => {
    setPageState('loading');
    setErrorMsg(null);

    try {
      // Step 3: Upload public key to register
      const res = await fetch('/api/users/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          public_key: keyPair.publicKey,
          key_type: 'Ed25519',
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || `注册失败 (${res.status})`);
      }

      const data = await res.json();
      const jwt = data.jwt || data.token;

      // Step 4: Download private key as .json backup file
      const backupData = {
        version: 1,
        key_type: 'Ed25519',
        created_at: new Date().toISOString(),
        public_key: keyPair.publicKey,
        private_key: keyPair.privateKey,
        note: '这是您 ClawsJoy 账号的私钥文件，请妥善保管。丢失后将无法恢复账号。',
      };
      const blob = new Blob([JSON.stringify(backupData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `clawsjoy-key-backup-${Date.now()}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      // Step 5: Save keys to localStorage
      localStorage.setItem('clawsjoy_private_key', keyPair.privateKey);
      localStorage.setItem('clawsjoy_public_key', keyPair.publicKey);
      localStorage.setItem('clawsjoy_jwt', jwt);

      setPageState('success');
      setTimeout(() => {
        router.push('/dashboard');
      }, 1500);
    } catch (err: any) {
      setErrorMsg(err.message || '注册流程完成失败');
      setPageState('error');
    }
  };

  // ===== Scenario 2: Login with Existing Key (Sign Challenge) =====
  const handleLogin = async () => {
    if (!storedPrivateKey || !storedPublicKey) return;
    setPageState('loading');
    setErrorMsg(null);
  // P1 测试：验证 write_file line 模式
    try {
      // Step 1: Request a challenge from server
      const challengeRes = await fetch('/api/users/challenge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ public_key: storedPublicKey }),
      });

      if (!challengeRes.ok) {
        const errData = await challengeRes.json().catch(() => ({}));
        throw new Error(errData.error || `获取 challenge 失败 (${challengeRes.status})`);
      }

      const { challenge } = await challengeRes.json();

      // Step 2: Sign the challenge with private key
      const signature = await signChallenge(storedPrivateKey, challenge);

      // Step 3: Send signed challenge to verify and get JWT
      const loginRes = await fetch('/api/users/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ public_key: storedPublicKey, signature }),
      });

      if (!loginRes.ok) {
        const errData = await loginRes.json().catch(() => ({}));
        throw new Error(errData.error || `登录失败 (${loginRes.status})`);
      }

      const data = await loginRes.json();
      const jwt = data.jwt || data.token;

      // Step 4: Save JWT to localStorage
      localStorage.setItem('clawsjoy_jwt', jwt);

      setPageState('success');
      setTimeout(() => {
        router.push('/dashboard');
      }, 1500);

    } catch (err: any) {
      setErrorMsg(err.message || '登录失败');
      setPageState('error');
    }
  };
  // ===== Scenario 3: Import Private Key from Backup File =====
  const handleImportKey = (jsonStr: string) => {
    try {
      const parsed = JSON.parse(jsonStr);

      // Validate the JSON structure
      if (!parsed.private_key || !parsed.public_key) {
        setErrorMsg('无效的私钥文件：缺少 private_key 或 public_key 字段');
        setPageState('error');
        return;
      }

      if (parsed.key_type && parsed.key_type !== 'Ed25519') {
        setErrorMsg('不支持的密钥类型：' + parsed.key_type);
        setPageState('error');
        return;
      }

      // Store keys in state and localStorage
      setStoredPrivateKey(parsed.private_key);
      setStoredPublicKey(parsed.public_key);
      localStorage.setItem('clawsjoy_private_key', parsed.private_key);
      localStorage.setItem('clawsjoy_public_key', parsed.public_key);

      // Call handleLogin to complete authentication
      handleLogin();
    } catch (err: any) {
      setErrorMsg('解析私钥文件失败：' + (err.message || 'JSON 格式错误'));
      setPageState('error');
    }
  };


  const [storedPrivateKey, setStoredPrivateKey] = useState<string | null>(null);
  const [storedPublicKey, setStoredPublicKey] = useState<string | null>(null);
  const [generatedKeyPair, setGeneratedKeyPair] = useState<KeyPair | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [progressText, setProgressText] = useState('');

  useEffect(() => {
    // On mount, check localStorage for stored keys
    const priv = localStorage.getItem('clawsjoy_private_key');
    const pub = localStorage.getItem('clawsjoy_public_key');
    if (priv && pub) {
      setStoredPrivateKey(priv);
      setStoredPublicKey(pub);
    }
  }, []);

  return (
    <div>
      <Head>
        <title>ClawsJoy 注册</title>
      </Head>

      <main style={{ maxWidth: 480, margin: '0 auto', padding: 24 }}>
        <h1>ClawsJoy 注册</h1>

        {pageState === 'error' && (
          <div style={{ color: 'red', marginBottom: 16 }}>{errorMsg}</div>
        )}

        {pageState === 'init' && (
          <div>
            <p>尚未拥有 ClawsJoy 账号？点击下方按钮开始注册。</p>
            <button onClick={handleStartRegister}>开始注册</button>
            <hr />
            <p>已有私钥？点击下方按钮登录或导入私钥文件。</p>
            <button onClick={() => setPageState('login')}>已有私钥，登录</button>
            <button onClick={() => setPageState('import_key')}>导入私钥文件</button>
          </div>
        )}

        {pageState === 'login' && (
          <div>
            <p>您已保存了私钥，点击下方按钮签名登录。</p>
            <button onClick={handleLogin} disabled={!storedPrivateKey}>
              使用私钥登录
            </button>
            <button onClick={() => setPageState('init')}>返回</button>
          </div>
        )}
        {pageState === 'import_key' && (
          <div>
            <p>请粘贴您的私钥备份文件（JSON）内容：</p>
            <textarea
              id="import-key-textarea"
              rows={8}
              style={{ width: '100%', fontFamily: 'monospace', fontSize: 12 }}
              placeholder="请在此粘贴私钥备份 JSON 内容..."
            />
            <br />
            <button onClick={() => {
              const ta = document.getElementById('import-key-textarea') as HTMLTextAreaElement;
              if (ta && ta.value) {
                handleImportKey(ta.value);
              } else {
                setErrorMsg('请先粘贴私钥 JSON 内容');
                setPageState('error');
              }
            }}>导入并登录</button>
            <button onClick={() => setPageState('init')}>返回</button>
          </div>
        )}

        {(pageState === 'generating' || pageState === 'loading') && (
          <div>
            <p>{progressText}</p>
          </div>
        )}

        {pageState === 'success' && (
          <div>
            <p style={{ color: 'green' }}>操作成功！即将跳转...</p>
          </div>
        )}
      </main>
    </div>
  );
};

export default RegisterPage;


// --- Test Validation ---
export function TestValidation(): { status: string; version: string } {
  return { status: "ok", version: "test" };
}


// --- Test Path Prefix ---
export function TestPathPrefix(): { status: string; path_test: boolean } {
  return { status: "ok", path_test: true };
}


  // ===== Logout: Clear stored keys =====
  const handleLogout = () => {
    localStorage.removeItem('clawsjoy_private_key');
    localStorage.removeItem('clawsjoy_public_key');
    localStorage.removeItem('clawsjoy_jwt');
    setStoredPrivateKey(null);
// 边界测试：第 390 行
    setStoredPublicKey(null);
    setPageState('init');
  };
