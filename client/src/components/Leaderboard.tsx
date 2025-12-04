import React, { useEffect, useState } from "react";
import { X, Trophy, Medal, Award, Star, TrendingUp, Crown } from "lucide-react";

interface LeaderboardProps {
  onClose: () => void;
  userId: string;
}

interface ScoreData {
  user_id: string;
  score: number;
}

interface TopPlayer extends ScoreData {
  rank: number;
}

export const Leaderboard: React.FC<LeaderboardProps> = ({ onClose, userId }) => {
  const [myScore, setMyScore] = useState<number | null>(null);
  const [topPlayers, setTopPlayers] = useState<TopPlayer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchScores = async () => {
      try {
        setLoading(true);
        setError(null);
        const [myScoreRes, topScoresRes] = await Promise.all([
          fetch(`/score/me?user_id=${encodeURIComponent(userId)}`),
          fetch(`/score/top?n=10`),
        ]);
        if (!myScoreRes.ok || !topScoresRes.ok) {
          throw new Error("Failed to fetch scores");
        }
        const myData = await myScoreRes.json();
        const topData = await topScoresRes.json();
        setMyScore(myData.score ?? 0);
        setTopPlayers(
          topData.top.map((player: ScoreData, index: number) => ({
            ...player,
            rank: index + 1,
          }))
        );
      } catch (err) {
        setError("Unable to load scores. Please try again.");
        console.error("Error fetching scores:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchScores();
  }, [userId]);

  const getRankIcon = (rank: number) => {
    switch (rank) {
      case 1:
        return <Crown className="text-yellow-400" size={28} />;
      case 2:
        return <Medal className="text-slate-300" size={24} />;
      case 3:
        return <Award className="text-orange-400" size={24} />;
      default:
        return <Star className="text-slate-500" size={20} />;
    }
  };

  const getRankBg = (rank: number) => {
    switch (rank) {
      case 1:
        return "from-yellow-500/20 to-orange-500/20 border-yellow-500/40";
      case 2:
        return "from-slate-400/20 to-slate-500/20 border-slate-400/40";
      case 3:
        return "from-orange-500/20 to-red-500/20 border-orange-500/40";
      default:
        return "from-slate-700/20 to-slate-800/20 border-slate-600/30";
    }
  };

  const myRank = topPlayers.findIndex((p) => p.user_id === userId) + 1;

  return (
    <div className="fixed inset-0 z-[10002] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
      <div className="relative bg-gradient-to-br from-slate-800 to-slate-900 rounded-3xl shadow-2xl border border-slate-700/50 max-w-2xl w-full max-h-[90vh] overflow-hidden animate-slideUp">
        <div className="absolute inset-0 bg-gradient-to-br from-yellow-500/5 to-orange-500/5 pointer-events-none" />
        <div className="absolute top-0 left-0 right-0 h-32 bg-gradient-to-b from-yellow-500/10 to-transparent pointer-events-none" />
        <div className="relative">
          <div className="flex items-center justify-between p-6 border-b border-slate-700/50">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-br from-yellow-500 to-orange-500 rounded-xl shadow-lg">
                <Trophy size={28} className="text-white" />
              </div>
              <div>
                <h2 className="text-2xl font-bold bg-gradient-to-r from-yellow-400 to-orange-400 bg-clip-text text-transparent">
                  Leaderboard
                </h2>
                <p className="text-slate-400 text-sm">Top players in NanoVerse</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-slate-700/50 rounded-full transition-colors"
              aria-label="Close"
            >
              <X size={24} className="text-slate-400" />
            </button>
          </div>
          <div className="p-6 overflow-y-auto max-h-[calc(90vh-180px)]">
            {loading ? (
              <div className="flex flex-col items-center justify-center py-12">
                <div className="animate-spin w-12 h-12 border-3 border-yellow-400 border-t-orange-400 rounded-full mb-4" />
                <p className="text-slate-400">Loading scores...</p>
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center py-12">
                <div className="p-4 bg-red-500/10 rounded-2xl mb-4">
                  <X size={32} className="text-red-400" />
                </div>
                <p className="text-red-400">{error}</p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="bg-gradient-to-br from-cyan-900/30 to-blue-900/30 rounded-2xl p-5 border border-cyan-500/30 shadow-lg">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-3 bg-cyan-500/20 rounded-xl">
                        <TrendingUp size={24} className="text-cyan-400" />
                      </div>
                      <div>
                        <p className="text-cyan-400 text-sm font-medium uppercase tracking-wide">
                          Your Score
                        </p>
                        <p className="text-white text-3xl font-bold">{myScore ?? 0}</p>
                      </div>
                    </div>
                    {myRank > 0 && (
                      <div className="text-right">
                        <p className="text-slate-400 text-xs uppercase tracking-wide">Rank</p>
                        <p className="text-cyan-400 text-2xl font-bold">#{myRank}</p>
                      </div>
                    )}
                  </div>
                </div>
                <div className="space-y-3">
                  <h3 className="text-lg font-semibold text-slate-300 flex items-center gap-2 px-2">
                    <Star className="text-yellow-400" size={18} /> Top Players
                  </h3>
                  {topPlayers.length === 0 ? (
                    <div className="text-center py-8 text-slate-400">
                      <Trophy size={48} className="mx-auto mb-3 opacity-30" />
                      <p>No scores yet. Be the first to play!</p>
                    </div>
                  ) : (
                    topPlayers.map((player) => {
                      const isCurrentUser = player.user_id === userId;
                      return (
                        <div
                          key={player.user_id}
                          className={`relative bg-gradient-to-r ${getRankBg(
                            player.rank
                          )} rounded-xl p-4 border transition-all duration-200 ${
                            isCurrentUser
                              ? "ring-2 ring-cyan-400 shadow-lg shadow-cyan-500/20"
                              : "hover:scale-[1.02]"
                          }`}
                        >
                          {player.rank <= 3 && (
                            <div className="absolute -top-2 -right-2 animate-float">
                              {getRankIcon(player.rank)}
                            </div>
                          )}
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                              <div
                                className={`flex items-center justify-center w-12 h-12 rounded-xl font-bold text-lg ${
                                  player.rank === 1
                                    ? "bg-gradient-to-br from-yellow-500 to-orange-500 text-white shadow-lg"
                                    : player.rank === 2
                                    ? "bg-gradient-to-br from-slate-400 to-slate-500 text-white shadow-md"
                                    : player.rank === 3
                                    ? "bg-gradient-to-br from-orange-500 to-red-500 text-white shadow-md"
                                    : "bg-slate-700/50 text-slate-300"
                                }`}
                              >
                                {player.rank}
                              </div>
                              <div>
                                <p
                                  className={`font-semibold ${
                                    isCurrentUser ? "text-cyan-300" : "text-white"
                                  }`}
                                >
                                  {isCurrentUser ? "You" : `Player ${player.user_id.slice(0, 8)}`}
                                </p>
                                <p className="text-slate-400 text-xs">
                                  ID: {player.user_id.slice(0, 12)}...
                                </p>
                              </div>
                            </div>
                            <div className="text-right">
                              <p
                                className={`text-2xl font-bold ${
                                  player.rank === 1
                                    ? "text-yellow-300"
                                    : player.rank === 2
                                    ? "text-slate-300"
                                    : player.rank === 3
                                    ? "text-orange-300"
                                    : "text-white"
                                }`}
                              >
                                {player.score}
                              </p>
                              <p className="text-slate-400 text-xs uppercase tracking-wide">
                                points
                              </p>
                            </div>
                          </div>
                          {isCurrentUser && (
                            <div className="absolute inset-0 rounded-xl border-2 border-cyan-400/20 pointer-events-none" />
                          )}
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

