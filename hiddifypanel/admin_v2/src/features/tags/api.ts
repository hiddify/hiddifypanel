import { getHttp } from '@/core/api/client'

export type TagColor = 'red' | 'orange' | 'green' | 'blue' | 'black'
export type TagKind = 'user'

export interface Tag {
  id: number
  name: string
  color: TagColor
  is_default: boolean
  /** How many users and admins have it. */
  count: number
}

interface TagList {
  tags: Tag[]
  colors: TagColor[]
}

export const tagsApi = {
  async list(): Promise<TagList> {
    const { data } = await getHttp().get<TagList>('tags/')
    return data
  },
  async create(name: string, color: TagColor): Promise<{ created_id: number } & TagList> {
    const { data } = await getHttp().post<{ created_id: number } & TagList>('tags/', { name, color })
    return data
  },
  async update(id: number, name: string, color: TagColor): Promise<TagList> {
    const { data } = await getHttp().patch<TagList>(`tags/${id}/`, { name, color })
    return data
  },
  async remove(id: number): Promise<TagList> {
    const { data } = await getHttp().delete<TagList>(`tags/${id}/`)
    return data
  },
  async assign(kind: TagKind, uuid: string, tagIds: number[]): Promise<number[]> {
    const { data } = await getHttp().put<{ tag_ids: number[] }>('tags/assign/', { kind, uuid, tag_ids: tagIds })
    return data.tag_ids
  },
  async bulk(kind: TagKind, uuids: string[], add: number[], remove: number[]): Promise<void> {
    await getHttp().post('tags/assign/', { kind, uuids, add, remove })
  },
}
