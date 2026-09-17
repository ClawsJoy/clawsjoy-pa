import type { NextPage } from 'next';
import Head from 'next/head';
import Link from 'next/link';
import { useEffect, useState } from 'react';

// --- Types ---
interface Agent {
  id: string;
  name: string;
  description: string;
  category: string;
  price: number;
  rating: number;
  developer: string;
  downloads: number;
  updatedAt: string;
}

type SortKey = 'rating' | 'downloads' | 'price' | 'updatedAt';

const CATEGORIES = [
  { value: '', label: '全部分类' },
  { value: 'customer_service', label: '客服' },
  { value: 'content', label: '内容' },
  { value: 'code', label: '代码' },
  { value: 'design', label: '设计' },
  { value: 'data_analysis', label: '数据分析' },
];

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: 'rating', label: '评分' },
  { value: 'downloads', label: '下载量' },
  { value: 'price', label: '价格' },
  { value: 'updatedAt', label: '更新时间' },
];

// --- Skeleton Card ---
const SkeletonCard = () => (
  <div className="animate-pulse bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-4">
    <div className="h-4 bg-gray-200 rounded w-3/4" />
    <div className="h-3 bg-gray-200 rounded w-full" />
    <div className="h-3 bg-gray-200 rounded w-5/6" />
    <div className="flex gap-2">
      <div className="h-5 bg-gray-200 rounded w-16" />
      <div className="h-5 bg-gray-200 rounded w-12" />
    </div>
    <div className="flex justify-between">
      <div className="h-3 bg-gray-200 rounded w-20" />
      <div className="h-3 bg-gray-200 rounded w-16" />
    </div>
  </div>
);

// --- Agent Card ---
const AgentCard = ({ agent }: { agent: Agent }) => {
  const categoryLabel = CATEGORIES.find((c) => c.value === agent.category)?.label || agent.category;

  return (
    <Link
      href={`/agents/${agent.id}`}
      className="block p-6 bg-white rounded-xl shadow-sm border border-gray-100 hover:shadow-md hover:border-indigo-200 transition-all duration-200 group"
    >
      {/* Name & Price */}
      <div className="flex items-start justify-between mb-2">
        <h3 className="text-lg font-semibold text-gray-900 group-hover:text-indigo-600 transition-colors">
          {agent.name}
        </h3>
        <span className="text-sm font-bold text-indigo-600 whitespace-nowrap ml-2">
          {agent.price === 0 ? '免费' : `¥${agent.price}`}
        </span>
      </div>

      {/* Description */}
      <p className="text-sm text-gray-500 line-clamp-2 mb-3">
        {agent.description}
      </p>

      {/* Category Tag */}
      <span className="inline-block px-2.5 py-0.5 text-xs font-medium rounded-full bg-indigo-50 text-indigo-700 mb-4">
        {categoryLabel}
      </span>

      {/* Meta: Rating · Developer · Downloads */}
      <div className="flex items-center gap-3 text-xs text-gray-400 mt-auto">
        <span className="flex items-center gap-1">
          <svg className="w-3.5 h-3.5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
          {agent.rating.toFixed(1)}
        </span>
        <span>{agent.developer}</span>
        <span className="flex items-center gap-1">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          {agent.downloads >= 1000 ? `${(agent.downloads / 1000).toFixed(1)}k` : agent.downloads}
        </span>
      </div>
    </Link>
  );
};

// --- Pagination Component ---
const PAGE_SIZE = 8;

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

const Pagination = ({ currentPage, totalPages, onPageChange }: PaginationProps) => {
  if (totalPages <= 1) return null;

  const getPageNumbers = () => {
    const pages: number[] = [];
    const maxVisible = 5;
    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let end = Math.min(totalPages, start + maxVisible - 1);
    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1);
    }
    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    return pages;
  };

  return (
    <div className="flex items-center justify-center gap-2 mt-8">
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage <= 1}
        className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        上一页
      </button>
      {getPageNumbers().map((page) => (
        <button
          key={page}
          onClick={() => onPageChange(page)}
          className={`w-9 h-9 text-sm rounded-lg transition-colors ${
            page === currentPage
              ? 'bg-indigo-600 text-white'
              : 'border border-gray-200 hover:bg-gray-50'
          }`}
        >
          {page}
        </button>
      ))}
      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage >= totalPages}
        className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        下一页
      </button>
    </div>
  );
};

// --- Main Page ---
const Home: NextPage = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [sortBy, setSortBy] = useState<SortKey>('rating');
  const [currentPage, setCurrentPage] = useState(1);

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchKeyword, selectedCategory, sortBy]);

  // --- Fetch agents ---
  useEffect(() => {
    const fetchAgents = async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        if (searchKeyword) params.set('keyword', searchKeyword);
        if (selectedCategory) params.set('category', selectedCategory);
        if (sortBy) params.set('sort', sortBy);
        const res = await fetch(`/api/agents?${params.toString()}`);
        const data = await res.json();
        setAgents(data.agents ?? []);
      } catch (err) {
        console.error('Failed to fetch agents', err);
        setAgents([]);
      } finally {
        setLoading(false);
      }
    };
    fetchAgents();
  }, [searchKeyword, selectedCategory, sortBy]);

  const totalPages = Math.max(1, Math.ceil(agents.length / PAGE_SIZE));
  const pagedAgents = agents.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-indigo-50">
      <Head>
        <title>ClawsJoy - Agent 市场</title>
        <meta name="description" content="Discover and deploy AI agents for your workflow" />
      </Head>

      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <Link href="/" className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
            ClawsJoy
          </Link>
          <nav className="flex gap-4">
            <Link href="/about" className="text-sm text-gray-600 hover:text-indigo-600 transition-colors">关于</Link>
            <Link href="/docs" className="text-sm text-gray-600 hover:text-indigo-600 transition-colors">文档</Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 pb-12 text-center">
        <h1 className="text-4xl sm:text-5xl font-extrabold text-gray-900 mb-4">
          AI Agent Marketplace
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          Discover powerful AI agents to automate your workflow, enhance productivity, and unlock new possibilities.
        </p>
      </section>

      {/* Filters */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-8">
        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
          <div className="flex gap-2 flex-wrap">
            {CATEGORIES.map((cat) => (
              <button
                key={cat.value}
                onClick={() => setSelectedCategory(cat.value)}
                className={`px-4 py-1.5 text-sm rounded-full transition-colors ${
                  selectedCategory === cat.value
                    ? 'bg-indigo-600 text-white'
                    : 'bg-white border border-gray-200 text-gray-600 hover:border-indigo-300'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>
          <div className="flex gap-3 items-center w-full sm:w-auto">
            <input
              type="text"
              placeholder="搜索 Agent..."
              value={searchKeyword}
              onChange={(e) => setSearchKeyword(e.target.value)}
              className="flex-1 sm:w-56 px-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent"
            />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortKey)}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {/* Agent Grid */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {loading
            ? Array.from({ length: 8 }).map((_, i) => <SkeletonCard key={i} />)
            : pagedAgents.length > 0
              ? pagedAgents.map((agent) => <AgentCard key={agent.id} agent={agent} />)
              : (
                <div className="col-span-full text-center py-16 text-gray-400">
                  未找到匹配的 Agent
                </div>
              )
          }
        </div>
        {!loading && <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={setCurrentPage} />}
      </section>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-sm text-gray-400">
          &copy; {new Date().getFullYear()} ClawsJoy. All rights reserved.
        </div>
      </footer>
    </div>
  );
};

export default Home;
