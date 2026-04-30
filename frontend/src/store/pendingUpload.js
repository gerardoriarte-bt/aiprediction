/**
 * Holds files + requirement + optional clientId between the launch
 * panel (e.g. SimsTab "new simulation" CTA) and the Process wizard.
 */
import { reactive } from 'vue'

const state = reactive({
  files: [],
  simulationRequirement: '',
  clientId: null,
  isPending: false
})

export function setPendingUpload(files, requirement, clientId = null) {
  state.files = files
  state.simulationRequirement = requirement
  state.clientId = clientId || null
  state.isPending = true
}

export function getPendingUpload() {
  return {
    files: state.files,
    simulationRequirement: state.simulationRequirement,
    clientId: state.clientId,
    isPending: state.isPending
  }
}

export function clearPendingUpload() {
  state.files = []
  state.simulationRequirement = ''
  state.clientId = null
  state.isPending = false
}

export default state
