import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import {
    BarChart,
    Bar,
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    PieChart,
    Pie,
    Cell,
} from 'recharts';
import {
    Users,
    MessageSquare,
    FileText,
    TrendingUp,
    Download,
    RefreshCw,
    Search,
    Filter,
    Eye,
    Activity,
    Clock,
    ThumbsUp,
    ThumbsDown,
} from 'lucide-react';
import { format } from 'date-fns';
import { fr } from 'date-fns/locale';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Types
interface AdminStats {
    total_conversations: number;
    total_messages: number;
    active_users_today: number;
    avg_response_time_ms: number;
    total_documents: number;
    feedback_positive: number;
    feedback_negative: number;
    conversations_by_day: Array<{ date: string; count: number }>;
    top_queries: Array<{ query: string; count: number }>;
    response_times: Array<{ hour: string; avg_ms: number }>;
    user_activity: Array<{ hour: string; users: number }>;
}

interface Conversation {
    id: string;
    user_id: string;
    user_name: string;
    message_count: number;
    created_at: string;
    last_activity: string;
    feedback?: 'positive' | 'negative';
}

// Carte statistique
function StatCard({
    title,
    value,
    icon: Icon,
    trend,
    color = 'blue',
}: {
    title: string;
    value: string | number;
    icon: React.ElementType;
    trend?: number;
    color?: string;
}) {
    const colorMap: Record<string, string> = {
          blue: 'bg-blue-600/20 text-blue-400',
          green: 'bg-green-600/20 text-green-400',
          purple: 'bg-purple-600/20 text-purple-400',
          orange: 'bg-orange-600/20 text-orange-400',
          red: 'bg-red-600/20 text-red-400',
    };

  return (
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
              <div className="flex items-center justify-between mb-4">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colorMap[color]}`}>
                                <Icon size={20} />
                      </div>div>
                {trend !== undefined && (
                    <span
                                  className={`text-xs font-medium ${
                                                  trend >= 0 ? 'text-green-400' : 'text-red-400'
                                  }`}
                                >
                      {trend >= 0 ? '+' : ''}{trend}%
                    </span>span>
                      )}
              </div>div>
              <p className="text-2xl font-bold text-white mb-1">{value}</p>p>
              <p className="text-gray-400 text-sm">{title}</p>p>
        </div>div>
      );
}

// Tableau conversations
function ConversationsTable({ conversations }: { conversations: Conversation[] }) {
    const [search, setSearch] = useState('');
    const [filter, setFilter] = useState<'all' | 'positive' | 'negative'>('all');
  
    const filtered = conversations.filter((conv) => {
          const matchSearch =
                  conv.user_name.toLowerCase().includes(search.toLowerCase()) ||
                  conv.id.includes(search);
          const matchFilter =
                  filter === 'all' || conv.feedback === filter;
          return matchSearch && matchFilter;
    });
  
    return (
          <div className="bg-gray-800 rounded-xl border border-gray-700">
                <div className="p-4 border-b border-gray-700 flex items-center gap-3">
                        <div className="flex-1 relative">
                                  <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                                  <input
                                                value={search}
                                                onChange={(e) => setSearch(e.target.value)}
                                                placeholder="Rechercher..."
                                                className="w-full bg-gray-900 border border-gray-700 rounded-lg pl-9 pr-4 py-2 text-gray-300 text-sm focus:outline-none focus:border-blue-500"
                                              />
                        </div>div>
                        <select
                                    value={filter}
                                    onChange={(e) => setFilter(e.target.value as typeof filter)}
                                    className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-gray-300 text-sm focus:outline-none"
                                  >
                                  <option value="all">Tous</option>option>
                                  <option value="positive">Positif</option>option>
                                  <option value="negative">Negatif</option>option>
                        </select>select>
                </div>div>
          
                <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                                  <thead>
                                              <tr className="border-b border-gray-700">
                                                            <th className="text-left p-4 text-gray-400 font-medium">Utilisateur</th>th>
                                                            <th className="text-left p-4 text-gray-400 font-medium">Messages</th>th>
                                                            <th className="text-left p-4 text-gray-400 font-medium">Date</th>th>
                                                            <th className="text-left p-4 text-gray-400 font-medium">Derniere activite</th>th>
                                                            <th className="text-left p-4 text-gray-400 font-medium">Feedback</th>th>
                                                            <th className="text-left p-4 text-gray-400 font-medium">Actions</th>th>
                                              </tr>tr>
                                  </thead>thead>
                                  <tbody>
                                    {filtered.map((conv) => (
                          <tr key={conv.id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                                          <td className="p-4">
                                                            <div>
                                                                                <p className="text-white font-medium">{conv.user_name}</p>p>
                                                                                <p className="text-gray-500 text-xs">{conv.id.slice(0, 8)}...</p>p>
                                                            </div>div>
                                          </td>td>
                                          <td className="p-4 text-gray-300">{conv.message_count}</td>td>
                                          <td className="p-4 text-gray-300">
                                            {format(new Date(conv.created_at), 'dd/MM/yyyy HH:mm', { locale: fr })}
                                          </td>td>
                                          <td className="p-4 text-gray-300">
                                            {format(new Date(conv.last_activity), 'HH:mm', { locale: fr })}
                                          </td>td>
                                          <td className="p-4">
                                            {conv.feedback === 'positive' && (
                                                <span className="flex items-center gap-1 text-green-400 text-xs">
                                                                      <ThumbsUp size={12} /> Positif
                                                </span>span>
                                                            )}
                                            {conv.feedback === 'negative' && (
                                                <span className="flex items-center gap-1 text-red-400 text-xs">
                                                                      <ThumbsDown size={12} /> Negatif
                                                </span>span>
                                                            )}
                                            {!conv.feedback && (
                                                <span className="text-gray-500 text-xs">-</span>span>
                                                            )}
                                          </td>td>
                                          <td className="p-4">
                                                            <button
                                                                                  className="p-1.5 rounded hover:bg-gray-700 text-gray-400 hover:text-white transition-colors"
                                                                                  title="Voir la conversation"
                                                                                >
                                                                                <Eye size={14} />
                                                            </button>button>
                                          </td>td>
                          </tr>tr>
                        ))}
                                  </tbody>tbody>
                        </table>table>
                  {filtered.length === 0 && (
                      <div className="p-8 text-center text-gray-500">Aucune conversation trouvee</div>div>
                        )}
                </div>div>
          </div>div>
        );
}

const CHART_COLORS = ['#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#ef4444'];

// Dashboard principal
export default function AdminDashboard() {
    const [activeTab, setActiveTab] = useState<'overview' | 'conversations' | 'documents'>('overview');
    const token = localStorage.getItem('access_token');
  
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
  
    const { data: stats, isLoading: statsLoading, refetch } = useQuery<AdminStats>({
          queryKey: ['admin-stats'],
          queryFn: () =>
                  axios.get(`${API_BASE}/api/v1/admin/stats`, { headers }).then((r) => r.data),
          refetchInterval: 30000,
    });
  
    const { data: conversations, isLoading: convsLoading } = useQuery<Conversation[]>({
          queryKey: ['admin-conversations'],
          queryFn: () =>
                  axios
                    .get(`${API_BASE}/api/v1/admin/conversations?limit=50`, { headers })
                    .then((r) => r.data.conversations),
          enabled: activeTab === 'conversations',
    });
  
    const handleExport = () => {
          const link = document.createElement('a');
          link.href = `${API_BASE}/api/v1/admin/export?format=csv`;
          link.setAttribute('Authorization', token || '');
          link.click();
    };
  
    const tabs = [
      { id: 'overview', label: 'Vue d\'ensemble', icon: Activity },
      { id: 'conversations', label: 'Conversations', icon: MessageSquare },
      { id: 'documents', label: 'Documents', icon: FileText },
        ] as const;
  
    return (
          <div className="flex flex-col h-full bg-gray-900 overflow-auto">
            {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700 bg-gray-900 sticky top-0 z-10">
                        <div>
                                  <h1 className="text-white font-bold text-lg">Tableau de bord Admin</h1>h1>
                                  <p className="text-gray-400 text-xs">Statistiques en temps reel</p>p>
                        </div>div>
                        <div className="flex items-center gap-2">
                                  <button
                                                onClick={() => refetch()}
                                                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm transition-colors"
                                              >
                                              <RefreshCw size={14} />
                                              Actualiser
                                  </button>button>
                                  <button
                                                onClick={handleExport}
                                                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm transition-colors"
                                              >
                                              <Download size={14} />
                                              Exporter CSV
                                  </button>button>
                        </div>div>
                </div>div>
          
            {/* Onglets */}
                <div className="flex gap-1 px-6 pt-4 border-b border-gray-700">
                  {tabs.map(({ id, label, icon: Icon }) => (
                      <button
                                    key={id}
                                    onClick={() => setActiveTab(id)}
                                    className={`flex items-center gap-2 px-4 py-2 rounded-t-lg text-sm font-medium transition-colors ${
                                                    activeTab === id
                                                      ? 'bg-gray-800 text-white border-t border-l border-r border-gray-700'
                                                      : 'text-gray-400 hover:text-white'
                                    }`}
                                  >
                                  <Icon size={14} />
                        {label}
                      </button>button>
                    ))}
                </div>div>
          
                <div className="flex-1 p-6">
                  {/* Vue d'ensemble */}
                  {activeTab === 'overview' && (
                      <div className="space-y-6">
                        {/* Cartes stats */}
                        {statsLoading ? (
                                      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                                        {[...Array(6)].map((_, i) => (
                                                          <div key={i} className="bg-gray-800 rounded-xl p-5 border border-gray-700 animate-pulse h-24" />
                                                        ))}
                                      </div>div>
                                    ) : stats ? (
                                      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
                                                      <StatCard
                                                                          title="Conversations totales"
                                                                          value={stats.total_conversations.toLocaleString()}
                                                                          icon={MessageSquare}
                                                                          trend={12}
                                                                          color="blue"
                                                                        />
                                                      <StatCard
                                                                          title="Messages totaux"
                                                                          value={stats.total_messages.toLocaleString()}
                                                                          icon={TrendingUp}
                                                                          trend={8}
                                                                          color="green"
                                                                        />
                                                      <StatCard
                                                                          title="Utilisateurs actifs (aujourd'hui)"
                                                                          value={stats.active_users_today}
                                                                          icon={Users}
                                                                          color="purple"
                                                                        />
                                                      <StatCard
                                                                          title="Temps de reponse moyen"
                                                                          value={`${Math.round(stats.avg_response_time_ms)}ms`}
                                                                          icon={Clock}
                                                                          color="orange"
                                                                        />
                                                      <StatCard
                                                                          title="Documents indexes"
                                                                          value={stats.total_documents.toLocaleString()}
                                                                          icon={FileText}
                                                                          color="blue"
                                                                        />
                                                      <StatCard
                                                                          title="Satisfaction"
                                                                          value={`${Math.round(
                                                                                                (stats.feedback_positive /
                                                                                                                       Math.max(stats.feedback_positive + stats.feedback_negative, 1)) *
                                                                                                  100
                                                                                              )}%`}
                                                                          icon={ThumbsUp}
                                                                          color="green"
                                                                        />
                                      </div>div>
                                    ) : null}
                      
                        {/* Graphiques */}
                        {stats && (
                                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                        {/* Conversations par jour */}
                                                      <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
                                                                        <h3 className="text-white font-medium mb-4">Conversations par jour</h3>h3>
                                                                        <ResponsiveContainer width="100%" height={200}>
                                                                                            <LineChart data={stats.conversations_by_day}>
                                                                                                                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                                                                                                  <XAxis dataKey="date" stroke="#9ca3af" tick={{ fontSize: 11 }} />
                                                                                                                  <YAxis stroke="#9ca3af" tick={{ fontSize: 11 }} />
                                                                                                                  <Tooltip
                                                                                                                                            contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
                                                                                                                                            labelStyle={{ color: '#f9fafb' }}
                                                                                                                                          />
                                                                                                                  <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2} dot={false} />
                                                                                              </LineChart>LineChart>
                                                                        </ResponsiveContainer>ResponsiveContainer>
                                                      </div>div>
                                      
                                        {/* Temps de reponse */}
                                                      <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
                                                                        <h3 className="text-white font-medium mb-4">Temps de reponse (ms)</h3>h3>
                                                                        <ResponsiveContainer width="100%" height={200}>
                                                                                            <BarChart data={stats.response_times}>
                                                                                                                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                                                                                                  <XAxis dataKey="hour" stroke="#9ca3af" tick={{ fontSize: 11 }} />
                                                                                                                  <YAxis stroke="#9ca3af" tick={{ fontSize: 11 }} />
                                                                                                                  <Tooltip
                                                                                                                                            contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
                                                                                                                                          />
                                                                                                                  <Bar dataKey="avg_ms" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                                                                                              </BarChart>BarChart>
                                                                        </ResponsiveContainer>ResponsiveContainer>
                                                      </div>div>
                                      
                                        {/* Satisfaction feedback */}
                                                      <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
                                                                        <h3 className="text-white font-medium mb-4">Feedback utilisateurs</h3>h3>
                                                                        <div className="flex items-center gap-6">
                                                                                            <ResponsiveContainer width={160} height={160}>
                                                                                                                  <PieChart>
                                                                                                                                          <Pie
                                                                                                                                                                      data={[
                                                                                                                                                                        { name: 'Positif', value: stats.feedback_positive },
                                                                                                                                                                        { name: 'Negatif', value: stats.feedback_negative },
                                                                                                                                                                                                  ]}
                                                                                                                                                                      cx="50%"
                                                                                                                                                                      cy="50%"
                                                                                                                                                                      innerRadius={50}
                                                                                                                                                                      outerRadius={70}
                                                                                                                                                                      paddingAngle={3}
                                                                                                                                                                      dataKey="value"
                                                                                                                                                                    >
                                                                                                                                                                    <Cell fill="#10b981" />
                                                                                                                                                                    <Cell fill="#ef4444" />
                                                                                                                                            </Pie>Pie>
                                                                                                                                          <Tooltip />
                                                                                                                    </PieChart>PieChart>
                                                                                              </ResponsiveContainer>ResponsiveContainer>
                                                                                            <div className="flex flex-col gap-3">
                                                                                                                  <div className="flex items-center gap-2">
                                                                                                                                          <div className="w-3 h-3 rounded-full bg-green-500" />
                                                                                                                                          <span className="text-gray-300 text-sm">
                                                                                                                                                                    Positif: {stats.feedback_positive}
                                                                                                                                            </span>span>
                                                                                                                    </div>div>
                                                                                                                  <div className="flex items-center gap-2">
                                                                                                                                          <div className="w-3 h-3 rounded-full bg-red-500" />
                                                                                                                                          <span className="text-gray-300 text-sm">
                                                                                                                                                                    Negatif: {stats.feedback_negative}
                                                                                                                                            </span>span>
                                                                                                                    </div>div>
                                                                                              </div>div>
                                                                        </div>div>
                                                      </div>div>
                                      
                                        {/* Top requetes */}
                                                      <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
                                                                        <h3 className="text-white font-medium mb-4">Questions frequentes</h3>h3>
                                                                        <div className="space-y-3">
                                                                          {stats.top_queries.slice(0, 5).map((q, idx) => (
                                                              <div key={idx} className="flex items-center gap-3">
                                                                                      <span className="text-gray-500 text-xs w-4">{idx + 1}</span>span>
                                                                                      <div className="flex-1">
                                                                                                                <p className="text-gray-300 text-xs truncate">{q.query}</p>p>
                                                                                                                <div
                                                                                                                                              className="h-1 bg-blue-600 rounded mt-1"
                                                                                                                                              style={{
                                                                                                                                                                              width: `${(q.count / (stats.top_queries[0]?.count || 1)) * 100}%`,
                                                                                                                                                }}
                                                                                                                                            />
                                                                                        </div>div>
                                                                                      <span className="text-gray-400 text-xs">{q.count}</span>span>
                                                              </div>div>
                                                            ))}
                                                                        </div>div>
                                                      </div>div>
                                      </div>div>
                                  )}
                      </div>div>
                        )}
                
                  {/* Conversations */}
                  {activeTab === 'conversations' && (
                      <div>
                        {convsLoading ? (
                                      <div className="bg-gray-800 rounded-xl p-8 text-center">
                                                      <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
                                      </div>div>
                                    ) : conversations ? (
                                      <ConversationsTable conversations={conversations} />
                                    ) : null}
                      </div>div>
                        )}
                
                  {/* Documents */}
                  {activeTab === 'documents' && (
                      <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                                  <div className="flex items-center justify-between mb-4">
                                                <h3 className="text-white font-medium">Documents indexes</h3>h3>
                                                <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm transition-colors">
                                                                <RefreshCw size={14} />
                                                                Re-indexer
                                                </button>button>
                                  </div>div>
                                  <p className="text-gray-400 text-sm">
                                                Affichage de la liste des documents disponibles dans Qdrant.
                                                Utilisez l'API <code className="text-blue-400">/api/v1/documents</code>code> pour la liste complete.
                                  </p>p>
                      </div>div>
                        )}
                </div>div>
          </div>div>
        );
}</div>
