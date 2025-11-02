
// import React, { useEffect, useMemo, useState } from 'react'
// import { MessageCircle, Wifi, WifiOff, Gamepad2, User } from 'lucide-react'
// import Sidebar from './components/Sidebar'
// import ChatInterface from './components/ChatInterface'
// import CustomizationPanel from './components/CustomizationPanel'
// import { useWebSocket } from './hooks/useWebSocket'
// import { useChat } from './hooks/useChat'

// function App() {
//   const [isConnecting, setIsConnecting] = useState(true)

//   // הוק ה-WS: מזהה משתמש לפי token ב-URL, מביא שחקנים פעילים, הודעות, היסטוריה וכו'
//   const {
//     isConnected,
//     messages,
//     selectedPlayer,
//     sendMessage,
//     selectPlayer,
//     // שינוי: במקום likeMessage אנחנו עובדים עם reactToMessage
//     reactToMessage,
//     activePlayers,
//     currentPlayerId,
//     unreadCounts,
//     markRead,
//   } = useWebSocket()

//   const {
//     currentTheme,
//     defaultThemes,
//     showCustomization,
//     setShowCustomization,
//     showEmojiPicker,
//     setShowEmojiPicker,
//     changeTheme,
//   } = useChat()

//   // החלת ערכת נושא
//   useEffect(() => {
//     changeTheme(currentTheme)
//   }, [currentTheme, changeTheme])

//   // מסך טעינה עד שה-WS נפתח וזוהה המשתמש הנוכחי
//   useEffect(() => {
//     if (isConnected && currentPlayerId) {
//       setIsConnecting(false)
//     }
//   }, [isConnected, currentPlayerId])

//   // סגירת פאנלים בלחיצה מחוץ
//   useEffect(() => {
//     const handleClickOutside = (event: MouseEvent) => {
//       if (!showCustomization && !showEmojiPicker) return
//       const target = event.target as HTMLElement
//       const outsideCustomization = !target.closest('.customization-panel')
//       const outsideEmoji = !target.closest('.emoji-picker')
//       if (outsideCustomization && outsideEmoji) {
//         setShowCustomization(false)
//         setShowEmojiPicker(false)
//       }
//     }
//     document.addEventListener('mousedown', handleClickOutside)
//     return () => document.removeEventListener('mousedown', handleClickOutside)
//   }, [showCustomization, showEmojiPicker, setShowCustomization, setShowEmojiPicker])

//   // חישוב סכום כל ההודעות שלא נקראו (אופציונלי להצגה ב-Header)
//   const totalUnread = useMemo(
//     () => Object.values(unreadCounts || {}).reduce((a, b) => a + (b || 0), 0),
//     [unreadCounts]
//   )

//   // מסך טעינה
//   if (isConnecting) {
//     return (
//       <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center">
//         <div className="text-center">
//           <div className="relative mb-6">
//             <div className="w-16 h-16 border-4 border-slate-600 border-t-cyan-500 rounded-full animate-spin" />
//             <Gamepad2 className="absolute inset-0 m-auto w-6 h-6 text-cyan-400" />
//           </div>
//           <h2 className="text-xl font-bold text-white mb-2">Connecting to Game Chat</h2>
//           <p className="text-slate-400">Establishing connection...</p>
//         </div>
//       </div>
//     )
//   }

//   return (
//     <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 text-white">
//       {/* Header */}
//       <header className="bg-slate-800/80 backdrop-blur-sm border-b border-slate-700 p-4">
//         <div className="flex items-center justify-between">
//           <div className="flex items-center gap-3">
//             <div className="p-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-500">
//               <MessageCircle className="w-6 h-6 text-white" />
//             </div>
//             <div>
//               <h1 className="text-xl font-bold">Game Chat</h1>
//               <p className="text-sm text-slate-400">
//                 Real-time communication for gamers
//                 {totalUnread > 0 && (
//                   <span className="ml-2 px-2 py-0.5 rounded-full bg-rose-600/80 text-white text-xs">
//                     {totalUnread > 99 ? '99+' : totalUnread} unread
//                   </span>
//                 )}
//               </p>
//             </div>
//           </div>

//           <div className="flex items-center gap-3">
//             {/* הצגת המשתמש הנוכחי לפי ה-token */}
//             <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-slate-700/60 border border-slate-600">
//               <User className="w-4 h-4 text-cyan-300" />
//               <span className="text-sm text-slate-200">
//                 {currentPlayerId || 'unknown'}
//               </span>
//             </div>

//             <div
//               className={`flex items-center gap-2 px-3 py-1 rounded-full ${
//                 isConnected
//                   ? 'bg-green-900/30 text-green-400'
//                   : 'bg-red-900/30 text-red-400'
//               }`}
//             >
//               {isConnected ? (
//                 <>
//                   <Wifi className="w-4 h-4" />
//                   <span className="text-sm font-medium">Connected</span>
//                 </>
//               ) : (
//                 <>
//                   <WifiOff className="w-4 h-4" />
//                   <span className="text-sm font-medium">Disconnected</span>
//                 </>
//               )}
//             </div>
//           </div>
//         </div>
//       </header>

//       {/* Main */}
//       <div className="flex h-[calc(100vh-80px)] relative">
//         <Sidebar
//           activePlayers={activePlayers}
//           selectedPlayer={selectedPlayer}
//           onSelectPlayer={selectPlayer}
//           currentPlayerId={currentPlayerId ?? ''}
//           unreadCounts={unreadCounts}
//           onMarkRead={markRead}
//         />

//         <ChatInterface
//           messages={messages}
//           selectedPlayer={selectedPlayer}
//           currentPlayerId={currentPlayerId ?? ''}
//           onSendMessage={sendMessage}
//           // שינוי: שולחים onReactMessage במקום onLikeMessage
//           onReactMessage={reactToMessage}
//           showEmojiPicker={showEmojiPicker}
//           setShowEmojiPicker={setShowEmojiPicker}
//           onCustomizationToggle={() => setShowCustomization(!showCustomization)}
//           onMarkRead={markRead}
//         />

//         {showCustomization && (
//           <div className="customization-panel">
//             <CustomizationPanel
//               currentTheme={currentTheme}
//               themes={defaultThemes}
//               onThemeChange={changeTheme}
//               onClose={() => setShowCustomization(false)}
//             />
//           </div>
//         )}
//       </div>

//       {/* Footer */}
//       <div className="bg-slate-800/50 border-t border-slate-700 p-2 text-center">
//         <p className="text-xs text-slate-400">
//           Game Chat v1.0 • Built for gamers, by gamers •{' '}
//           <span className="text-cyan-400">{activePlayers.length} players online</span>
//         </p>
//       </div>
//     </div>
//   )
// }

// export default App
import React, { useEffect, useMemo, useState } from 'react'
import { MessageCircle, Wifi, WifiOff, Gamepad2, User } from 'lucide-react'
import Sidebar from './components/Sidebar'
import ChatInterface from './components/ChatInterface'
import CustomizationPanel from './components/CustomizationPanel'
import { useWebSocket } from './hooks/useWebSocket'
import { useChat } from './hooks/useChat'

function App() {
  const [isConnecting, setIsConnecting] = useState(true)

  // הוק ה-WS: מזהה משתמש לפי token ב-URL, מביא שחקנים פעילים, הודעות, היסטוריה וכו'
  const {
    isConnected,
    messages,
    selectedPlayer,
    sendMessage,
    selectPlayer,
    // שינוי: במקום likeMessage אנחנו עובדים עם reactToMessage
    reactToMessage,
    activePlayers,
    currentPlayerId,
    unreadCounts,
    markRead,
    /** NEW: מחיקה רכה של הודעה */
    deleteMessage,
  } = useWebSocket()

  const {
    currentTheme,
    defaultThemes,
    showCustomization,
    setShowCustomization,
    showEmojiPicker,
    setShowEmojiPicker,
    changeTheme,
  } = useChat()

  // החלת ערכת נושא
  useEffect(() => {
    changeTheme(currentTheme)
  }, [currentTheme, changeTheme])

  // מסך טעינה עד שה-WS נפתח וזוהה המשתמש הנוכחי
  useEffect(() => {
    if (isConnected && currentPlayerId) {
      setIsConnecting(false)
    }
  }, [isConnected, currentPlayerId])

  // סגירת פאנלים בלחיצה מחוץ
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (!showCustomization && !showEmojiPicker) return
      const target = event.target as HTMLElement
      const outsideCustomization = !target.closest('.customization-panel')
      const outsideEmoji = !target.closest('.emoji-picker')
      if (outsideCustomization && outsideEmoji) {
        setShowCustomization(false)
        setShowEmojiPicker(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showCustomization, showEmojiPicker, setShowCustomization, setShowEmojiPicker])

  // חישוב סכום כל ההודעות שלא נקראו (אופציונלי להצגה ב-Header)
  const totalUnread = useMemo(
    () => Object.values(unreadCounts || {}).reduce((a, b) => a + (b || 0), 0),
    [unreadCounts]
  )

  // מסך טעינה
  if (isConnecting) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center">
        <div className="text-center">
          <div className="relative mb-6">
            <div className="w-16 h-16 border-4 border-slate-600 border-t-cyan-500 rounded-full animate-spin" />
            <Gamepad2 className="absolute inset-0 m-auto w-6 h-6 text-cyan-400" />
          </div>
          <h2 className="text-xl font-bold text-white mb-2">Connecting to Game Chat</h2>
          <p className="text-slate-400">Establishing connection...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 text-white">
      {/* Header */}
      <header className="bg-slate-800/80 backdrop-blur-sm border-b border-slate-700 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-500">
              <MessageCircle className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold">Game Chat</h1>
              <p className="text-sm text-slate-400">
                Talk. Play. Enjoy.
                {totalUnread > 0 && (
                  <span className="ml-2 px-2 py-0.5 rounded-full bg-rose-600/80 text-white text-xs">
                    {totalUnread > 99 ? '99+' : totalUnread} unread
                  </span>
                )}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* הצגת המשתמש הנוכחי לפי ה-token */}
            <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-slate-700/60 border border-slate-600">
              <User className="w-4 h-4 text-cyan-300" />
              <span className="text-sm text-slate-200">
                {currentPlayerId || 'unknown'}
              </span>
            </div>

            <div
              className={`flex items-center gap-2 px-3 py-1 rounded-full ${
                isConnected
                  ? 'bg-green-900/30 text-green-400'
                  : 'bg-red-900/30 text-red-400'
              }`}
            >
              {isConnected ? (
                <>
                  <Wifi className="w-4 h-4" />
                  <span className="text-sm font-medium">Connected</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-4 h-4" />
                  <span className="text-sm font-medium">Disconnected</span>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main */}
      <div className="flex h-[calc(100vh-80px)] relative">
        <Sidebar
          activePlayers={activePlayers}
          selectedPlayer={selectedPlayer}
          onSelectPlayer={selectPlayer}
          currentPlayerId={currentPlayerId ?? ''}
          unreadCounts={unreadCounts}
          onMarkRead={markRead}
        />

        <ChatInterface
          messages={messages}
          selectedPlayer={selectedPlayer}
          currentPlayerId={currentPlayerId ?? ''}
          onSendMessage={sendMessage}
          // שינוי: שולחים onReactMessage במקום onLikeMessage
          onReactMessage={reactToMessage}
          /** NEW: מחיקה רכה עוברת ל-ChatInterface ומשם ל-MessageItem */
          onDeleteMessage={deleteMessage}
          showEmojiPicker={showEmojiPicker}
          setShowEmojiPicker={setShowEmojiPicker}
          onCustomizationToggle={() => setShowCustomization(!showCustomization)}
          onMarkRead={markRead}
        />

        {showCustomization && (
          <div className="customization-panel">
            <CustomizationPanel
              currentTheme={currentTheme}
              themes={defaultThemes}
              onThemeChange={changeTheme}
              onClose={() => setShowCustomization(false)}
            />
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="bg-slate-800/50 border-t border-slate-700 p-2 text-center">
        <p className="text-xs text-slate-400">
          Game Chat v1.0 • Built for gamers, by gamers •{' '}
          <span className="text-cyan-400">{activePlayers.length} players online</span>
        </p>
      </div>
    </div>
  )
}

export default App
