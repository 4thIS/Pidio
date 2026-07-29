// 인앱 다이얼로그(브라우저 prompt/confirm 대체) — Promise 기반.
// dialog.prompt(title, default) → Promise<string|null>
// dialog.confirm(title, {message}) → Promise<boolean>
// dialog.choice(title, choices[{label,value,danger}], {message}) → Promise<value|null>
import { reactive } from 'vue'

export const dialogState = reactive({
  open: false,
  mode: 'confirm',
  title: '',
  message: '',
  value: '',
  placeholder: '',
  confirmText: '확인',
  cancelText: '취소',
  choices: null,
  _resolve: null,
})

function open(opts) {
  return new Promise((resolve) => {
    Object.assign(
      dialogState,
      {
        open: true, mode: 'confirm', title: '', message: '', value: '', placeholder: '',
        confirmText: '확인', cancelText: '취소', choices: null,
      },
      opts,
      { _resolve: resolve },
    )
  })
}

export const dialog = {
  prompt(title, defaultValue = '', opts = {}) {
    return open({ mode: 'prompt', title, value: defaultValue, ...opts })
  },
  confirm(title, opts = {}) {
    return open({ mode: 'confirm', title, ...opts })
  },
  choice(title, choices, opts = {}) {
    return open({ mode: 'choice', title, choices, ...opts })
  },
}

export function resolveDialog(result) {
  dialogState.open = false
  const r = dialogState._resolve
  dialogState._resolve = null
  if (r) r(result)
}
