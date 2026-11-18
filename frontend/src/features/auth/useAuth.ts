import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, ApiError } from '@/lib/api'

export type Role = 'admin' | 'viewer'

export type User = {
  id: string
  email: string
  full_name: string
  role: Role
}

export type LoginInput = { email: string; password: string }

export const meQueryKey = ['auth', 'me'] as const

async function fetchMe(): Promise<User | null> {
  try {
    return await api<User>('/auth/me')
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) return null
    throw err
  }
}

/** The signed-in user, or null when nobody is signed in. */
export function useMe() {
  return useQuery({
    queryKey: meQueryKey,
    queryFn: fetchMe,
    staleTime: 5 * 60_000,
  })
}

export function useLogin() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: LoginInput) =>
      api<{ user: User }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify(input),
      }),
    onSuccess: ({ user }) => {
      queryClient.setQueryData(meQueryKey, user)
    },
  })
}

export function useLogout() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api<void>('/auth/logout', { method: 'POST' }),
    onSettled: () => {
      // Drop everything cached for the previous user, then mark as signed out.
      queryClient.clear()
      queryClient.setQueryData(meQueryKey, null)
    },
  })
}
