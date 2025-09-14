import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

// Define interfaces for strong typing of your data
export interface Chunk {
  id: number;
  content: string;
  start_char: number;
  end_char: number;
  embedding_id: number | null;
}

export interface EmbeddingData {
  id: number;
  chunk_id: number;
  vector: number[];
}

@Injectable({
  providedIn: 'root'
})
export class PdfService {
  // Define the base URL for your Flask API
  private apiUrl = 'http://localhost:5000/api';

  constructor(private http: HttpClient) { }


  private getAuthHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    return new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });
  }


  getChunks(fileId: number): Observable<{ chunks: Chunk[] }> {
    return this.http.get<{ chunks: Chunk[] }>(`${this.apiUrl}/get_chunks/${fileId}`, {
      headers: this.getAuthHeaders(),
      withCredentials: true
    });
  }


  getEmbedding(embeddingId: number): Observable<EmbeddingData> {
    return this.http.get<EmbeddingData>(`${this.apiUrl}/get_embedding/${embeddingId}`, {
      headers: this.getAuthHeaders(),
      withCredentials: true
    });
  }
}
