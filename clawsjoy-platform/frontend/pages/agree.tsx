import type { NextPage } from 'next';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';

const VALID_TYPES = ['platform', 'agent', 'developer'] as const;

const AgreePage: NextPage = () => {
  const router = useRouter();
  const { type } = router.query;

  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [agreed, setAgreed] = useState(false);
  const [signing, setSigning] = useState(false);

  // Fetch agreement content
  useEffect(() => {
    if (!type || typeof type !== 'string') {
      setError('请选择协议类型');
      setLoading(false);
      return;
    }

    if (!VALID_TYPES.includes(type as typeof VALID_TYPES[number])) {
      setError('请选择协议类型');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    fetch(`/api/agreements/${encodeURIComponent(type)}`)
      .then((res) => {
        if (!res.ok) throw new Error(`获取协议失败 (${res.status})`);
        return res.text();
      })
      .then((text) => {
        setContent(text);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [type]);

  // Handle sign
  const handleSign = async () => {
    if (!agreed || signing || !type || typeof type !== 'string') return;

    setSigning(true);
    try {
      const res = await fetch('/api/agreements/sign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agreement_type: type, version: '1.1' }),
      });

      if (!res.ok) throw new Error(`签署失败 (${res.status})`);

      // Redirect to home on success
      await router.push('/');
    } catch (err: any) {
      setError(err.message);
      setSigning(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Head>
        <title>{type ? `${type} - 协议` : '协议'} - ClawsJoy</title>
      </Head>

      <main className="flex-1 max-w-3xl mx-auto w-full px-4 py-8">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 md:p-8">
          <h1 className="text-2xl font-bold text-gray-900 mb-6">
            {type ? `${type}协议` : '用户协议'}
          </h1>

          {/* Loading */}
          {loading && (
            <div className="space-y-3 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-full" />
              <div className="h-4 bg-gray-200 rounded w-5/6" />
              <div className="h-4 bg-gray-200 rounded w-4/5" />
              <div className="h-4 bg-gray-200 rounded w-full" />
              <div className="h-4 bg-gray-200 rounded w-3/4" />
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
              {error}
            </div>
          )}

          {/* Content */}
          {!loading && !error && content && (
            <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-a:text-blue-600 prose-code:text-pink-600 prose-pre:bg-gray-50">
              <ReactMarkdown>{content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Checkbox + Sign */}
        {!loading && !error && content && (
          <div className="mt-6 bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={agreed}
                onChange={(e) => setAgreed(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-600 leading-relaxed">
                我已阅读并同意上述协议内容
              </span>
            </label>

            <button
              type="button"
              disabled={!agreed || signing}
              onClick={handleSign}
              className={`mt-4 w-full py-2.5 px-4 rounded-lg font-medium text-sm transition-colors ${
                agreed && !signing
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
            >
              {signing ? '签署中...' : '签署协议'}
            </button>
          </div>
        )}
      </main>
    </div>
  );
};

export default AgreePage;
