import LivePreview from '../components/dashboard/LivePreview'
import SystemStatus from '../components/dashboard/SystemStatus'
import QuickConfig from '../components/dashboard/QuickConfig'
import ChatPanel from '../components/chat/ChatPanel'

export default function DashboardPage() {
  return (
    <div className="flex flex-col p-6 gap-6 h-full overflow-hidden">
      <div className="grid grid-cols-12 grid-rows-12 gap-6 h-full">
        <div className="col-span-12 lg:col-span-5 row-span-7">
          <LivePreview />
        </div>
        <div className="col-span-12 lg:col-span-7 row-span-4">
          <SystemStatus />
        </div>
        <div className="col-span-12 lg:col-span-7 row-span-3">
          <QuickConfig />
        </div>
        <div className="col-span-12 row-span-5">
          <ChatPanel />
        </div>
      </div>
    </div>
  )
}
