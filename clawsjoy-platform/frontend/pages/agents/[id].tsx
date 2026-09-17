import type { NextPage } from 'next';
import { useRouter } from 'next/router';
import { useEffect, useState, useCallback } from 'react';
import Head from 'next/head';
import Link from 'next/link';

// --- Types ---
interface Review {
  id: string;
  userId: string;
  userName: string;
  rating: number;
  comment: string;
  createdAt: string;
}

interface AgentDetail {
  id: string;
  name: string;
  description: string;
  category: string;
  price: number;
  rating: number;
  downloads: number;
  developer: string;
  developerAvatar?: string;
  developerBio?: string;
  status: string;
  createdAt: string;
  updatedAt: string;
  reviews: Review[];
}

const CATEGORIES: { value: string; label: string }[] = [
  { value: '', label: '全部分类' },
  { value: 'customer_service', label: '客服' },
  { value: 'content', label: '内容' },
  { value: 'code', label: '代码' },
  { value: 'design', label: '设计' },
  { value: 'data_analysis', label: '数据分析' },
];

// --- Helpers ---
const getCategoryLabel = (value: string): string =>
  CATEGORIES.find((c) => c.value === value)?.label || value;

const formatPrice = (price: number): string =>
  price === 0 ? '免费' : `\u00a5${price.toFixed(2)}`;

const formatNumber = (n: number): string => {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
};

const renderStars = (rating: number) => {
  const full = Math.floor(rating);
  const half = rating - full >= 0.5;
  const stars: JSX.Element[] = [];
  for (let i = 0; i < 5; i++) {
    if (i < full) {
      stars.push(
        <svg key={i} className="w-4 h-4 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      );
    } else if (half && i === full) {
      stars.push(
        <svg key={i} className="w-4 h-4 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
          <defs>
            <linearGradient id={`half-${i}`}>
              <stop offset="50%" stopColor="currentColor" />
              <stop offset="50%" stopColor="#D1D5DB" />
            </linearGradient>
          </defs>
          <path fill={`url(#half-${i})`} d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      );
    } else {
      stars.push(
        <svg key={i} className="w-4 h-4 text-gray-300" fill="currentColor" viewBox="0 0 20 20">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      );
    }
  }
  return <div className="flex items-center">{stars}</div>;
};

// --- Sub-components ---
const DetailSkeleton = () => (
  <div className="min-h-screen bg-gray-50 flex items-center justify-center">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
  </div>
);

const ErrorState = ({ message, onRetry }: { message: string; onRetry: () => void }) => (
  <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center gap-4">
    <div className="text-red-500 text-lg">{message}</div>
    <button
      onClick={onRetry}
      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
    >
      重试
    </button>
  </div>
);

const ReviewsSection = ({ reviews }: { reviews: Review[] }) => (
  <div className="bg-white rounded-xl shadow-sm p-6">
    <h2 className="text-lg font-bold text-gray-900 mb-4">评价 ({reviews.length})</h2>
    {reviews.length === 0 ? (
      <p className="text-gray-400 text-sm">暂无评价</p>
    ) : (
      <div className="space-y-4">
        {reviews.map((review) => (
          <div key={review.id} className="border-b border-gray-100 pb-4 last:border-0 last:pb-0">
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-gray-900">{review.userName}</span>
              <span className="text-sm text-gray-400">{review.createdAt}</span>
            </div>
            <div className="mb-1">{renderStars(review.rating)}</div>
            <p className="text-gray-600 text-sm">{review.comment}</p>
          </div>
        ))}
      </div>
    )}
  </div>
);

// --- Main Page ---
const AgentDetailPage: NextPage = () => {
  const router = useRouter();
  const { id } = router.query;
  const [agent, setAgent] = useState<AgentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [subscribing, setSubscribing] = useState(false);

  const fetchAgent = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/agents/${id}`);
      if (!res.ok) throw new Error(`请求失败 (${res.status})`);
      const data = await res.json();
      setAgent(data);
    } catch (err: any) {
      setError(err.message || '加载失败');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchAgent();
  }, [fetchAgent]);

  const handleSubscribe = async () => {
    // 检查 JWT
    const jwt = localStorage.getItem('clawsjoy_jwt');
    if (!jwt) {
      router.push('/register');
      return;
    }
    // 已登录，调订阅接口
    setSubscribing(true);
    try {
      const res = await fetch(`/api/agents/${id}/subscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${jwt}`,
        },
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.message || `订阅失败 (${res.status})`);
      }
      alert('订阅完成，即将跳转。');
    } catch (err: any) {
      alert(err.message || '订阅失败，请稍后重试');
    } finally {
      setSubscribing(false);
    }
  };

  if (loading) return <DetailSkeleton />;
  if (error) return <ErrorState message={error} onRetry={fetchAgent} />;
  if (!agent) return <ErrorState message="未找到该 Agent" onRetry={fetchAgent} />;

  return (
    <div className="min-h-screen bg-gray-50">
      <Head>
        <title>{agent.name} - ClawsJoy</title>
      </Head>

      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="text-xl font-bold text-blue-600">
            ClawsJoy
          </Link>
          <nav className="flex items-center gap-4">
            <Link href="/" className="text-gray-600 hover:text-gray-900 transition-colors">
              首页
            </Link>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Agent Info Card */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-6">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-gray-900 mb-2">{agent.name}</h1>
              <div className="flex items-center gap-3 mb-3">
                <span className="inline-block px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded-full">
                  {getCategoryLabel(agent.category)}
                </span>
                <span className="text-sm text-gray-400">
                  {renderStars(agent.rating)} {agent.rating.toFixed(1)}
                </span>
                <span className="text-sm text-gray-400">
                  {formatNumber(agent.downloads)} 下载
                </span>
              </div>
              <p className="text-gray-600 mb-4">{agent.description}</p>
              <div className="flex items-center gap-4">
                <span className="text-2xl font-bold text-blue-600">
                  {formatPrice(agent.price)}
                </span>
                <button
                  onClick={handleSubscribe}
                  disabled={subscribing}
                  className={`px-6 py-2.5 rounded-lg font-medium text-white transition-colors ${
                    subscribing
                      ? 'bg-gray-400 cursor-not-allowed'
                      : 'bg-blue-600 hover:bg-blue-700'
                  }`}
                >
                  {subscribing ? '订阅中...' : '订阅'}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Developer Info */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-6">
          <h2 className="text-lg font-bold text-gray-900 mb-3">开发者</h2>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center text-gray-500 font-medium">
              {agent.developer.charAt(0).toUpperCase()}
            </div>
            <div>
              <p className="font-medium text-gray-900">{agent.developer}</p>
              {agent.developerBio && (
                <p className="text-sm text-gray-500">{agent.developerBio}</p>
              )}
            </div>
          </div>
        </div>

        {/* Details */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-6">
          <h2 className="text-lg font-bold text-gray-900 mb-3">详细信息</h2>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-400">状态</span>
              <p className="text-gray-900">{agent.status === 'active' ? '已发布' : agent.status}</p>
            </div>
            <div>
              <span className="text-gray-400">发布时间</span>
              <p className="text-gray-900">{agent.createdAt}</p>
            </div>
            <div>
              <span className="text-gray-400">更新时间</span>
              <p className="text-gray-900">{agent.updatedAt}</p>
            </div>
          </div>
        </div>

        {/* Reviews */}
        <ReviewsSection reviews={agent.reviews} />
      </main>
    </div>
  );
};

export default AgentDetailPage;
