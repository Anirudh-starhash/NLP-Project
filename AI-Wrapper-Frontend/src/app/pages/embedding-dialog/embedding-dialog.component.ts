import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';


export interface EmbeddingData {
  id: number;
  chunk_id: number;
  vector: number[];
}

@Component({
  selector: 'app-embedding-dialog',
  standalone: true,

  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatCardModule
  ],
  templateUrl: './embedding-dialog.component.html',
  styleUrls: ['./embedding-dialog.component.css']
})
export class EmbeddingDialogComponent {
  constructor(@Inject(MAT_DIALOG_DATA) public data: EmbeddingData) { }
}
