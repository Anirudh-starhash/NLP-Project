import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit {
  isSidebarOpen = true;
  isDragging = false;
  fileName: string | null = null;
  uploadedPdfs: any[] = []; // List of PDFs

  constructor(private httpClient: HttpClient) {}

  ngOnInit() {
    this.fetchUploadedPdfs();
  }

  toggleSidebar() {
    this.isSidebarOpen = !this.isSidebarOpen;
  }

  onDragOver(event: DragEvent) {
    event.preventDefault();
    this.isDragging = true;
  }

  onDragLeave(event: DragEvent) {
    event.preventDefault();
    this.isDragging = false;
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    this.isDragging = false;
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.handleFile(files[0]);
    }
  }

  onFileSelected(event: Event) {
    const element = event.currentTarget as HTMLInputElement;
    const files = element.files;
    if (files && files.length > 0) {
      this.handleFile(files[0]);
    }
  }

  uploadFile(file: File) {
    const token = localStorage.getItem('access_token');
    const formData = new FormData();
    formData.append('file', file);

    this.httpClient.post('http://localhost:5000/api/upload_pdf', formData, {
      headers: {
        'Authorization': `Bearer ${token}`
      },
      withCredentials: true
    }).subscribe({
      next: (response: any) => {
        console.log('Upload successful', response);
        alert('File uploaded successfully!');
        this.fetchUploadedPdfs(); // refresh list
      },
      error: (error) => {
        console.error('Upload error', error);
        alert('Failed to upload file.');
      }
    });
  }


  fetchUploadedPdfs() {
    const token = localStorage.getItem('access_token'); // get the stored token

    this.httpClient.get('http://localhost:5000/api/get_pdfs', {
      headers: {
        'Authorization': `Bearer ${token}`
      },
      withCredentials: true
    }).subscribe({
      next: (response: any) => {
        this.uploadedPdfs = response.pdfs.map((pdf: any) => ({
          ...pdf,
          upload_time: new Date(pdf.upload_time + 'Z').toLocaleString() // Convert to local timezone
        }));
      },
      error: (error) => {
        console.error('Error fetching PDFs', error);
      }
    });
  }


  private handleFile(file: File) {
    if (file.type === "application/pdf") {
      console.log('PDF File selected:', file);
      this.fileName = file.name;
      this.uploadFile(file);
    } else {
      alert('Please select a valid PDF file.');
      this.fileName = null;
    }
  }
}
