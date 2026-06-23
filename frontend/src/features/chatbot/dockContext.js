import { createContext, useContext } from 'react'

// Shared open/minimized + active-tab state for the persistent chat dock.
// Provided by Layout so the dock survives route changes; consumed by the
// dock itself and by the sidebar "Assistant" opener.
export const DockContext = createContext({
  open: true,
  setOpen: () => {},
  tab: 'chat',
  setTab: () => {},
})

export const useDock = () => useContext(DockContext)
