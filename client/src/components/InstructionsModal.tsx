import React from 'react';
import { X, Keyboard, MessageSquare, Palette, Bot } from 'lucide-react';

interface InstructionsModalProps {
  onClose: () => void;
}

export const InstructionsModal: React.FC<InstructionsModalProps> = ({ onClose }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="relative bg-gradient-to-br from-slate-800 to-slate-900 rounded-3xl shadow-2xl border border-slate-700/50 max-w-2xl w-full max-h-[90vh] overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-slate-700/50">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-500 rounded-xl">
              <Keyboard size={24} className="text-white" />
            </div>
            <h2 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              How to Play
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-700/50 rounded-full transition-colors"
          >
            <X size={24} className="text-slate-400" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
          <div className="space-y-6">
            <section>
              <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                <Keyboard size={20} className="text-blue-400" />
                Movement Controls
              </h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/30">
                  <div className="flex items-center gap-3 mb-2">
                    <kbd className="px-3 py-1.5 bg-slate-700 rounded-lg text-sm font-mono text-slate-200">W</kbd>
                    <span className="text-slate-300">or</span>
                    <kbd className="px-3 py-1.5 bg-slate-700 rounded-lg text-sm font-mono text-slate-200">↑</kbd>
                  </div>
                  <p className="text-sm text-slate-400">Move up</p>
                </div>

                <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/30">
                  <div className="flex items-center gap-3 mb-2">
                    <kbd className="px-3 py-1.5 bg-slate-700 rounded-lg text-sm font-mono text-slate-200">S</kbd>
                    <span className="text-slate-300">or</span>
                    <kbd className="px-3 py-1.5 bg-slate-700 rounded-lg text-sm font-mono text-slate-200">↓</kbd>
                  </div>
                  <p className="text-sm text-slate-400">Move down</p>
                </div>

                <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/30">
                  <div className="flex items-center gap-3 mb-2">
                    <kbd className="px-3 py-1.5 bg-slate-700 rounded-lg text-sm font-mono text-slate-200">A</kbd>
                    <span className="text-slate-300">or</span>
                    <kbd className="px-3 py-1.5 bg-slate-700 rounded-lg text-sm font-mono text-slate-200">←</kbd>
                  </div>
                  <p className="text-sm text-slate-400">Move left</p>
                </div>

                <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/30">
                  <div className="flex items-center gap-3 mb-2">
                    <kbd className="px-3 py-1.5 bg-slate-700 rounded-lg text-sm font-mono text-slate-200">D</kbd>
                    <span className="text-slate-300">or</span>
                    <kbd className="px-3 py-1.5 bg-slate-700 rounded-lg text-sm font-mono text-slate-200">→</kbd>
                  </div>
                  <p className="text-sm text-slate-400">Move right</p>
                </div>
              </div>
            </section>

            <section>
              <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                <MessageSquare size={20} className="text-purple-400" />
                Message Controls
              </h3>
              <div className="bg-gradient-to-br from-purple-900/30 to-purple-800/20 rounded-xl p-5 border border-purple-500/30">
                <div className="flex items-start gap-4">
                  <kbd className="px-4 py-2 bg-purple-700/50 rounded-lg text-lg font-mono text-purple-200">M</kbd>
                  <div className="flex-1">
                    <h4 className="text-white font-semibold mb-1">Leave a Message</h4>
                    <p className="text-slate-300 text-sm">
                      Press M to leave a message on your current square for others to discover.
                    </p>
                  </div>
                </div>
              </div>
            </section>

            <section>
              <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                <Palette size={20} className="text-pink-400" />
                Color Controls
              </h3>
              <div className="bg-gradient-to-br from-pink-900/30 to-pink-800/20 rounded-xl p-5 border border-pink-500/30">
                <div className="flex items-start gap-4">
                  <kbd className="px-4 py-2 bg-pink-700/50 rounded-lg text-lg font-mono text-pink-200">C</kbd>
                  <div className="flex-1">
                    <h4 className="text-white font-semibold mb-1">Change Color</h4>
                    <p className="text-slate-300 text-sm">
                      Press C to cycle through different colors and paint the world.
                    </p>
                  </div>
                </div>
              </div>
            </section>

            <section>
              <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                <Bot size={20} className="text-green-400" />
                Bot Mode
              </h3>
              <div className="bg-gradient-to-br from-green-900/30 to-green-800/20 rounded-xl p-5 border border-green-500/30">
                <div className="space-y-3">
                  <div className="flex items-start gap-3">
                    <div className="w-2 h-2 rounded-full bg-green-400 mt-2" />
                    <p className="text-slate-300 text-sm flex-1">
                      Click the <span className="font-semibold text-green-300">Bot Toggle</span> button to activate autonomous mode.
                    </p>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-2 h-2 rounded-full bg-green-400 mt-2" />
                    <p className="text-slate-300 text-sm flex-1">
                      The AI bot will take control and explore the world automatically.
                    </p>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-2 h-2 rounded-full bg-green-400 mt-2" />
                    <p className="text-slate-300 text-sm flex-1">
                      The bot will move, change colors on its own.
                    </p>
                  </div>
                </div>
              </div>
            </section>

            <div className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 rounded-xl p-4 border border-blue-500/20">
              <p className="text-slate-300 text-sm text-center">
                Explore the voxel world manually or let the AI bot explore for you!
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
